using System;

namespace System.Windows.Forms
{
    public enum DialogResult { None = 0, OK = 1, Cancel = 2, Abort = 3, Retry = 4, Ignore = 5, Yes = 6, No = 7 }

    public enum MessageBoxButtons { OK = 0, OKCancel = 1, AbortRetryIgnore = 2, YesNoCancel = 3, YesNo = 4, RetryCancel = 5 }

    public enum MessageBoxDefaultButton { Button1 = 0, Button2 = 256, Button3 = 512, Button4 = 768 }

    [Flags]
    public enum MessageBoxOptions { DefaultDesktopOnly = 131072, RightAlign = 524288, RtlReading = 1048576, ServiceNotification = 2097152 }

    public interface IWin32Window { IntPtr Handle { get; } }

    public enum MessageBoxIcon { None = 0, Error = 16, Hand = 16, Stop = 16, Question = 32, Exclamation = 48, Warning = 48, Asterisk = 64, Information = 64 }

    public static class MessageBox
    {
        static DialogResult Log(string text, string caption)
        {
            try { Console.Error.WriteLine("[headless MessageBox] " + caption + ": " + text); } catch { }
            return DialogResult.OK;
        }

        public static DialogResult Show(string text) => Log(text, "");
        public static DialogResult Show(string text, string caption) => Log(text, caption);
        public static DialogResult Show(string text, string caption, MessageBoxButtons buttons) => Log(text, caption);
        public static DialogResult Show(string text, string caption, MessageBoxButtons buttons, MessageBoxIcon icon) => Log(text, caption);
        public static DialogResult Show(string text, string caption, MessageBoxButtons buttons, MessageBoxIcon icon, MessageBoxDefaultButton defaultButton) => Log(text, caption);
        public static DialogResult Show(string text, string caption, MessageBoxButtons buttons, MessageBoxIcon icon, MessageBoxDefaultButton defaultButton, MessageBoxOptions options) => Log(text, caption);
        public static DialogResult Show(IWin32Window owner, string text) => Log(text, "");
        public static DialogResult Show(IWin32Window owner, string text, string caption) => Log(text, caption);
        public static DialogResult Show(IWin32Window owner, string text, string caption, MessageBoxButtons buttons) => Log(text, caption);
        public static DialogResult Show(IWin32Window owner, string text, string caption, MessageBoxButtons buttons, MessageBoxIcon icon) => Log(text, caption);
    }
}
