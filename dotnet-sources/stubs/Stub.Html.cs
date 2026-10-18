
using System.Collections.Generic;
using BUTR.CrashReport.Models;

namespace BUTR.CrashReport.Renderer.Html
{
    public static class CrashReportHtml
    {
        public static string AddData(string htmlReport, string gzipBase64CrashReportJson, string gZipBase64MiniDump, string gZipBase64SaveFile, string base64Screenshot)
        {
            return htmlReport;
        }

        public static string Build(CrashReportModel crashReportModel, IEnumerable<LogSource> files)
        {
            return string.Empty;
        }
    }
}
