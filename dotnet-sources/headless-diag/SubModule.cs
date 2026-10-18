using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using HarmonyLib;
using TaleWorlds.MountAndBlade;

namespace HeadlessDiag
{
    public class SubModule : MBSubModuleBase
    {
        static readonly string[] LogCandidates =
        {
            Environment.GetEnvironmentVariable("HEADLESS_DIAG_LOG"),
            @"Z:\home\container\data\headless-diag.log",
            @"Z:\data\headless-diag.log",
            Path.Combine(Path.GetTempPath(), "headless-diag.log"),
        };

        const int MaxDistinctFirstChance = 150;

        static StreamWriter _writer;
        static string _logPath;
        static readonly List<string> _openErrors = new List<string>();
        static int _firstChance;
        static readonly Dictionary<string, int> _firstChanceSeen = new Dictionary<string, int>();
        static int _beforeRootCalls;
        static bool _harmonyHooked;
        static bool _harmonyReported;
        static readonly HashSet<string> _fixNotLoadedLogged = new HashSet<string>();
        static bool _fixesApplied;
        static bool _ticked;
        static DateTime _lastAlive = DateTime.MinValue;
        static long _tickCount;

        static void Write(string line)
        {
            var text = $"[{DateTime.UtcNow:HH:mm:ss.fff}] {line}";
            if (_writer != null)
            {
                try { _writer.WriteLine(text); } catch { }
            }
            else
            {
                try { Console.Error.WriteLine("[HeadlessDiag] " + text); } catch { }
            }
        }

        static void OpenLog()
        {
            foreach (var path in LogCandidates)
            {
                if (string.IsNullOrWhiteSpace(path)) continue;
                try
                {
                    var dir = Path.GetDirectoryName(path);
                    if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                    {
                        _openErrors.Add($"{path}: directory {dir} does not exist");
                        continue;
                    }
                    _writer = new StreamWriter(path, append: false, encoding: new UTF8Encoding(false)) { AutoFlush = true };
                    _logPath = path;
                    return;
                }
                catch (Exception ex)
                {
                    _openErrors.Add($"{path}: {ex.GetType().Name}: {ex.Message}");
                }
            }
        }

        static SubModule()
        {
            Init();
        }

        static bool _inited;
        static void Init()
        {
            if (_inited) return;
            _inited = true;
            OpenLog();
            foreach (var err in _openErrors) Write("log open failed -> " + err);
            if (_writer == null)
            {
                Write("no log file could be opened; console (stderr) only");
            }

            Write("=== HeadlessDiag online ===");
            Write("log file: " + (_logPath ?? "(none)"));
            Write("runtime: " + Environment.Version + "  os: " + Environment.OSVersion + "  pid: " + Environment.ProcessId);
            Write("cwd: " + Environment.CurrentDirectory);
            Write("cmdline: " + Environment.CommandLine);

            AppDomain.CurrentDomain.FirstChanceException += (s, e) =>
            {
                _firstChance++;
                var key = e.Exception.GetType().FullName + ": " + e.Exception.Message;
                int seen;
                lock (_firstChanceSeen)
                {
                    _firstChanceSeen.TryGetValue(key, out seen);
                    seen++;
                    if (seen == 1 && _firstChanceSeen.Count >= MaxDistinctFirstChance) return;
                    _firstChanceSeen[key] = seen;
                }
                if (seen > 3)
                {
                    if (seen % 500 == 0) Write($"FIRST-CHANCE (repeat x{seen}): {key}");
                    return;
                }
                Write($"FIRST-CHANCE #{_firstChance}{(seen > 1 ? $" (repeat {seen})" : "")}: {key}");
                Write("  at: " + (e.Exception.StackTrace ?? "(no stack)"));
                WriteFrames(e.Exception);
                if (seen == 1) WriteLiveStack();
                if (e.Exception.InnerException != null)
                    Write("  inner: " + e.Exception.InnerException);

                if (e.Exception is ReflectionTypeLoadException rtle && rtle.LoaderExceptions != null)
                    foreach (var le in rtle.LoaderExceptions)
                        Write("  loader: " + le);
            };

            InstallFallbackResolver();

            AppDomain.CurrentDomain.UnhandledException += (s, e) =>
                Write("UNHANDLED (terminating=" + e.IsTerminating + "): " + e.ExceptionObject);

            AppDomain.CurrentDomain.ProcessExit += (s, e) => Write("=== ProcessExit ===");

            AppDomain.CurrentDomain.AssemblyLoad += (s, e) =>
                Write("assembly-load: " + e.LoadedAssembly.GetName().Name + " " + e.LoadedAssembly.GetName().Version
                      + "  [" + SafeLocation(e.LoadedAssembly) + "]");

        }

        protected override void OnSubModuleLoad()
        {
            Init();
            ReportHarmony();
            ApplyHeadlessFixes();
            CheckModuleInfos();
            Write("--- OnSubModuleLoad complete ---");
        }

        static void WriteFrames(Exception ex)
        {
            try
            {
                foreach (var f in new System.Diagnostics.StackTrace(ex, false).GetFrames())
                {
                    var m = f.GetMethod();
                    Write($"    frame: {m?.DeclaringType?.FullName}::{m?.Name} IL_{f.GetILOffset():X4} [{m?.Module?.Assembly?.GetName().Name}]");
                }
            }
            catch { }
        }

        static void WriteLiveStack()
        {
            try
            {
                var frames = new System.Diagnostics.StackTrace(2, false).GetFrames();
                for (int i = 0; i < frames.Length && i < 40; i++)
                {
                    var m = frames[i].GetMethod();
                    Write($"    caller[{i}]: {m?.DeclaringType?.FullName}::{m?.Name} IL_{frames[i].GetILOffset():X4} [{m?.Module?.Assembly?.GetName().Name}]");
                }
            }
            catch { }
        }

        static void WriteMapInfo()
        {
            try
            {
                var campaignType = Type.GetType("TaleWorlds.CampaignSystem.Campaign, TaleWorlds.CampaignSystem");
                var current = campaignType?.GetProperty("Current", BindingFlags.Public | BindingFlags.Static)?.GetValue(null);
                if (current == null) return;
                var wrapper = campaignType.GetProperty("MapSceneWrapper")?.GetValue(current);
                var size = wrapper?.GetType().GetMethod("GetTerrainSize")?.Invoke(wrapper, null);
                var dim = campaignType.GetProperty("DefaultWeatherNodeDimension")?.GetValue(current);
                var diag = campaignType.GetProperty("MapDiagonal", BindingFlags.Public | BindingFlags.Static)?.GetValue(null);
                Write($"map: wrapper={wrapper?.GetType().FullName} terrainSize={size} weatherDim={dim} mapDiagonal={diag}");
            }
            catch (Exception e) { Write("map info failed: " + e.GetType().Name); }
        }

        static string SafeLocation(Assembly a)
        {
            try { return string.IsNullOrEmpty(a.Location) ? "(dynamic/in-memory)" : a.Location; }
            catch { return "(unknown)"; }
        }

        static void ReportHarmony()
        {
            try
            {
                var harmonies = AppDomain.CurrentDomain.GetAssemblies()
                    .Where(a => a.GetName().Name == "0Harmony").ToList();
                if (harmonies.Count == 0) { Write("harmony: 0Harmony not loaded yet"); return; }
                if (!_harmonyReported)
                {
                    _harmonyReported = true;
                    foreach (var asm in harmonies)
                        Write("harmony: 0Harmony " + asm.GetName().Version + " at " + SafeLocation(asm));
                }

                if (_harmonyHooked) return;
                if (Environment.GetEnvironmentVariable("HEADLESS_DIAG_HARMONY") != "1") return;
                var asm0 = harmonies[0];
                var fileLog = asm0.GetType("HarmonyLib.FileLog");
                fileLog?.GetProperty("LogWriter", BindingFlags.Public | BindingFlags.Static)?.SetValue(null, _writer);
                var harmony = asm0.GetType("HarmonyLib.Harmony");
                harmony?.GetField("DEBUG", BindingFlags.Public | BindingFlags.Static)?.SetValue(null, true);
                _harmonyHooked = true;
                Write("harmony: DEBUG on, FileLog redirected here (HEADLESS_DIAG_HARMONY=1)");
            }
            catch (Exception ex) { Write("harmony: report failed: " + ex); }
        }

        static readonly System.Collections.Generic.HashSet<string> _resolving = new System.Collections.Generic.HashSet<string>();

        static void InstallFallbackResolver()
        {
            try
            {
                var here = Path.GetDirectoryName(typeof(SubModule).Assembly.Location);
                var modules = Path.GetFullPath(Path.Combine(here, "..", "..", ".."));
                var engineBin = Path.GetFullPath(Path.Combine(modules, "..", "bin", "Win64_Shipping_Server"));
                AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
                {
                    var name = new AssemblyName(e.Name).Name;
                    lock (_resolving) { if (!_resolving.Add(name)) return null; }
                    try
                    {
                        var candidates = new System.Collections.Generic.List<string> { Path.Combine(engineBin, name + ".dll"), Path.Combine(engineBin, "Microsoft.WindowsDesktop.App", name + ".dll") };
                        if (Directory.Exists(modules))
                            foreach (var m in Directory.GetDirectories(modules))
                                candidates.Add(Path.Combine(m, "bin", "Win64_Shipping_Server", name + ".dll"));
                        foreach (var c in candidates)
                            if (File.Exists(c))
                            {
                                Write("resolver: " + name + " loaded from " + c);
                                return Assembly.LoadFrom(c);
                            }
                    }
                    catch { }
                    finally { lock (_resolving) _resolving.Remove(name); }
                    return null;
                };
                Write("resolver: fallback assembly lookup installed (engine folder, game desktop-runtime folder, then each module's server folder)");
            }
            catch (Exception ex) { Write("resolver: install failed: " + ex.Message); }
        }

        static void CheckModuleInfos()
        {
            try
            {
                var utils = Type.GetType("TaleWorlds.Engine.Utilities, TaleWorlds.Engine");
                var helper = Type.GetType("TaleWorlds.ModuleManager.ModuleHelper, TaleWorlds.ModuleManager");
                var names = (string[])utils?.GetMethod("GetModulesNames", BindingFlags.Public | BindingFlags.Static)?.Invoke(null, null);
                var get = helper?.GetMethod("GetModuleInfo", BindingFlags.Public | BindingFlags.Static, null, new[] { typeof(string) }, null);
                if (names == null || get == null) { Write("modules: lookup not available"); return; }
                int bad = 0;
                foreach (var n in names)
                {
                    object info = null;
                    try { info = get.Invoke(null, new object[] { n }); } catch { }
                    if (info == null) { bad++; Write("modules: ModuleHelper.GetModuleInfo('" + n + "') returned null (a mod that lists all modules will crash on it)"); }
                }
                Write($"modules: {names.Length} module name(s), {bad} without module info");
            }
            catch (Exception e) { Write("modules: check failed: " + e.GetType().Name); }
        }

        static bool _eoeFixed, _weatherFixed, _rosterFixed;
        static int _rosterSuppressed;
        static int _weatherSuppressed;

        static void ApplyHeadlessFixes()
        {
            if (!_eoeFixed) _eoeFixed = TrySkipMethod("Bannerlord.EOEPatches.SubModule", "OnBeforeInitialModuleScreenSetAsRoot");
            if (!_weatherFixed) _weatherFixed = TryFinalizeWeather();
            if (!_rosterFixed) _rosterFixed = TrySwallowNull("TaleWorlds.Core.MBEquipmentRoster", "AddEquipmentRoster");
            _fixesApplied = _eoeFixed && _weatherFixed && _rosterFixed;
        }

        static bool TryFinalizeWeather()
        {
            try
            {
                var type = AppDomain.CurrentDomain.GetAssemblies()
                    .Select(a => { try { return a.GetType("TaleWorlds.CampaignSystem.GameComponents.DefaultMapWeatherModel", false); } catch { return null; } })
                    .FirstOrDefault(t => t != null);
                if (type == null) return false;
                var target = AccessTools.Method(type, "GetWeatherEventInPosition");
                if (target == null) { Write("fix: DefaultMapWeatherModel.GetWeatherEventInPosition not found"); return false; }
                new Harmony("headlessdiag.weather").Patch(target, finalizer: new HarmonyMethod(AccessTools.Method(typeof(SubModule), nameof(WeatherFinalizer))));
                Write("fix: weather lookups outside the weather grid now return Clear instead of throwing (total-conversion maps)");
                return true;
            }
            catch (Exception ex) { Write("fix: weather finalizer failed: " + ex.Message); return false; }
        }

        static bool TrySwallowNull(string typeName, string methodName)
        {
            try
            {
                var type = AppDomain.CurrentDomain.GetAssemblies()
                    .Select(a => { try { return a.GetType(typeName, false); } catch { return null; } })
                    .FirstOrDefault(t => t != null);
                if (type == null) return false;
                var target = AccessTools.Method(type, methodName);
                if (target == null) return false;
                new Harmony("headlessdiag.nullswallow").Patch(target, prefix: new HarmonyMethod(AccessTools.Method(typeof(SubModule), nameof(RosterPrefix))));
                Write($"fix: {typeName}.{methodName} skips null equipment rosters (a mod XML names a roster that failed to load)");
                return true;
            }
            catch (Exception ex) { Write("fix: null swallow failed: " + ex.Message); return false; }
        }

        public static bool RosterPrefix(object equipmentRoster)
        {
            if (equipmentRoster != null) return true;
            if (System.Threading.Interlocked.Increment(ref _rosterSuppressed) <= 3) Write("roster: null equipment roster skipped");
            return false;
        }

        public static Exception WeatherFinalizer(Exception __exception, ref TaleWorlds.CampaignSystem.ComponentInterfaces.MapWeatherModel.WeatherEvent __result)
        {
            if (__exception == null) return null;
            __result = TaleWorlds.CampaignSystem.ComponentInterfaces.MapWeatherModel.WeatherEvent.Clear;
            if (System.Threading.Interlocked.Increment(ref _weatherSuppressed) == 1) Write("weather: first out-of-grid lookup suppressed (" + __exception.GetType().Name + ")");
            return null;
        }

        static bool TrySkipMethod(string typeName, string methodName)
        {
            try
            {
                var type = AppDomain.CurrentDomain.GetAssemblies()
                    .Select(a => { try { return a.GetType(typeName, false); } catch { return null; } })
                    .FirstOrDefault(t => t != null);
                if (type == null)
                {
                    if (_fixNotLoadedLogged.Add(typeName)) Write($"fix: {typeName} not loaded yet (further checks not logged)");
                    return false;
                }

                var target = AccessTools.Method(type, methodName);
                if (target == null) { Write($"fix: {typeName}.{methodName} not found"); return false; }

                new Harmony("headlessdiag.fixes").Patch(
                    target,
                    prefix: new HarmonyMethod(AccessTools.Method(typeof(SubModule), nameof(SkipOriginal))));
                Write($"fix: skipping {typeName}.{methodName} (client-only, unsafe headless)");
                return true;
            }
            catch (Exception ex) { Write($"fix: failed to patch {typeName}.{methodName}: {ex}"); return false; }
        }

        static bool SkipOriginal() => false;

        static void DumpModuleState(string where)
        {
            try
            {
                var names = AppDomain.CurrentDomain.GetAssemblies()
                    .Select(a => a.GetName().Name + " " + a.GetName().Version)
                    .Where(n => n.StartsWith("Bannerlord.") || n.StartsWith("0Harmony") || n.StartsWith("Coop")
                                || n.StartsWith("MonoMod") || n.StartsWith("HeadlessDiag") || n.StartsWith("Mono.Cecil"))
                    .OrderBy(n => n).ToList();
                Write($"modules @ {where}: {names.Count} relevant assemblies loaded");
                foreach (var n in names) Write("  loaded: " + n);
                Write("  Bannerlord.Harmony module assembly loaded: "
                      + AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == "Bannerlord.Harmony"));
            }
            catch (Exception ex) { Write("module dump failed: " + ex); }
        }

        protected override void OnBeforeInitialModuleScreenSetAsRoot()
        {
            _beforeRootCalls++;
            ReportHarmony();
            ApplyHeadlessFixes();
            if (_beforeRootCalls > 1) return;
            Write(">>> OnBeforeInitialModuleScreenSetAsRoot (this is where mods patch; later repeat calls are not logged)");
            DumpModuleState("OnBeforeInitialModuleScreenSetAsRoot");
        }

        protected override void OnGameStart(TaleWorlds.Core.Game game, TaleWorlds.Core.IGameStarter starter)
            => Write(">>> OnGameStart");

        protected override void OnApplicationTick(float dt)
        {
            _tickCount++;
            if (!_ticked)
            {
                _ticked = true;
                Write(">>> first application tick - module init survived");
                DumpModuleState("first tick");
            }
            var now = DateTime.UtcNow;
            if ((now - _lastAlive).TotalSeconds >= 60)
            {
                _lastAlive = now;
                WriteMapInfo();
                Write($"alive: ticks={_tickCount} firstChance={_firstChance} distinct={_firstChanceSeen.Count} beforeRootCalls={_beforeRootCalls} gc={GC.CollectionCount(0)}/{GC.CollectionCount(1)}/{GC.CollectionCount(2)} mem={GC.GetTotalMemory(false) / (1024 * 1024)}MB");
            }
        }
    }
}
