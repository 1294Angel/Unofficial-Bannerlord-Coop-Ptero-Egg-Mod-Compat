
using System;
using System.Collections.Generic;
using BUTR.CrashReport.Interfaces;
using BUTR.CrashReport.Models;

namespace BUTR.CrashReport.Renderer.ImGui
{

    public interface ICrashReportRendererUtilities
    {
        IEnumerable<string> GetNativeLibrariesFolderPath();
        void Upload(CrashReportModel crashReport, ICollection<LogSource> logSources);
        void CopyAsHtml(CrashReportModel crashReport, ICollection<LogSource> logSources);
        void SaveCrashReportAsHtml(CrashReportModel crashReport, ICollection<LogSource> logSources, bool addMiniDump, bool addLatestSave, bool addScreenshots);
        void SaveCrashReportAsZip(CrashReportModel crashReport, ICollection<LogSource> logSources);
    }

    public static class CrashReportImGui
    {
        public static void ShowAndWait(
            Exception exception,
            IList<LogSource> logSources,
            Dictionary<string, string> additionalMetadata,
            ICrashReportMetadataProvider crashReportMetadataProvider,
            IStacktraceFilter stacktraceFilter,
            IAssemblyUtilities assemblyUtilities,
            IModuleProvider moduleProvider,
            ILoaderPluginProvider loaderPluginProvider,
            IHarmonyProvider harmonyProvider,
            IModelConverter modelConverter,
            IPathAnonymizer pathAnonymizer,
            ICrashReportRendererUtilities crashReportRendererUtilities)
        {
            Report(exception?.ToString());
        }

        public static void ShowAndWait(
            CrashReportModel crashReportModel,
            IList<LogSource> logSources,
            ICrashReportRendererUtilities crashReportRendererUtilities)
        {
            Report(null);
        }

        private static void Report(string detail)
        {
            try
            {
                Console.WriteLine("[ButterLib] Crash report suppressed - ImGui renderer is unavailable on a headless server.");
                if (!string.IsNullOrEmpty(detail)) Console.WriteLine(detail);
            }
            catch
            {

            }
        }
    }
}
