
using System.Collections.Generic;
using BUTR.CrashReport.Models;

namespace BUTR.CrashReport.Renderer.WinForms
{
    public interface ICrashReportRendererUtilities
    {
        void Upload(CrashReportModel crashReport, ICollection<LogSource> logSources);
        string CopyAsHtml(CrashReportModel crashReport, ICollection<LogSource> logSources);
        void SaveCrashReportAsHtml(CrashReportModel crashReport, ICollection<LogSource> logSources, bool addMiniDump, bool addLatestSave, bool addScreenshots);
    }

    public class CrashReportWinForms
    {
        public bool IncludeMiniDump { get; set; }
        public bool IncludeSaveFile { get; set; }
        public bool IncludeScreenshot { get; set; }

        public CrashReportWinForms(CrashReportModel crashReport, ICollection<LogSource> logSources, ICrashReportRendererUtilities crashReportRendererUtilities)
        {
        }

        public void SetIncludeMiniDump(bool value) { IncludeMiniDump = value; }
        public void SetIncludeSaveFile(bool value) { IncludeSaveFile = value; }
        public void SetIncludeScreenshot(bool value) { IncludeScreenshot = value; }

        public void CopyAsHTML() { }
        public void UploadReport() { }
        public void SaveReport() { }
    }
}
