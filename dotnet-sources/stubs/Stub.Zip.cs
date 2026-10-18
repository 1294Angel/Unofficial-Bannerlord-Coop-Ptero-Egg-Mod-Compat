
using System.IO;

namespace BUTR.CrashReport.Renderer.Zip
{
    public static class CrashReportZip
    {
        public static Stream Build(Stream crashReportJson, Stream logsJson, Stream miniDump, Stream saveFile, Stream screenshot)
        {
            return new MemoryStream();
        }
    }
}
