Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class Audio {
    [DllImport("winmm.dll", EntryPoint = "waveInGetNumDevs", SetLastError = true)]
    public static extern uint waveInGetNumDevs();

    [DllImport("winmm.dll", EntryPoint = "waveInOpen", SetLastError = true)]
    public static extern uint waveInOpen(out IntPtr hWaveIn, uint uDeviceID, ref WAVEFORMATEX lpFormat, IntPtr dwCallback, IntPtr dwInstance, uint dwFlags);

    [DllImport("winmm.dll", EntryPoint = "waveInPrepareHeader", SetLastError = true)]
    public static extern uint waveInPrepareHeader(IntPtr hWaveIn, ref WAVEHDR lpWaveInHdr, uint uSize);

    [DllImport("winmm.dll", EntryPoint = "waveInAddBuffer", SetLastError = true)]
    public static extern uint waveInAddBuffer(IntPtr hWaveIn, ref WAVEHDR lpWaveInHdr, uint uSize);

    [DllImport("winmm.dll", EntryPoint = "waveInStart", SetLastError = true)]
    public static extern uint waveInStart(IntPtr hWaveIn);

    [DllImport("winmm.dll", EntryPoint = "waveInStop", SetLastError = true)]
    public static extern uint waveInStop(IntPtr hWaveIn);

    [StructLayout(LayoutKind.Sequential)]
    public struct WAVEFORMATEX {
        public ushort wFormatTag;
        public ushort nChannels;
        public uint nSamplesPerSec;
        public uint nAvgBytesPerSec;
        public ushort nBlockAlign;
        public ushort wBitsPerSample;
        public ushort cbSize;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct WAVEHDR {
        public IntPtr lpData;
        public uint dwBufferLength;
        public uint dwBytesRecorded;
        public IntPtr dwUser;
        public uint dwFlags;
        public uint dwLoops;
        public IntPtr lpNext;
        public IntPtr reserved;
    }
}
"@

$format = New-Object Audio+WAVEFORMATEX
$format.wFormatTag = 1 # WAVE_FORMAT_PCM
$format.nChannels = 1
$format.nSamplesPerSec = 16000
$format.wBitsPerSample = 16
$format.nBlockAlign = ($format.nChannels * $format.wBitsPerSample / 8)
$format.nAvgBytesPerSec = ($format.nSamplesPerSec * $format.nBlockAlign)
$format.cbSize = 0

$hWaveIn = [IntPtr]::Zero
$result = [Audio]::waveInOpen([ref]$hWaveIn, 0, [ref]$format, [IntPtr]::Zero, [IntPtr]::Zero, 0)

if ($result -ne 0) {
    Write-Error "Failed to open audio device: $result"
    exit
}

$bufferSize = 16000 * 2 # 1 second of 16-bit audio
$buffer = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($bufferSize)

$header = New-Object Audio+WAVEHDR
$header.lpData = $buffer
$header.dwBufferLength = $bufferSize

[Audio]::waveInPrepareHeader($hWaveIn, [ref]$header, [System.Runtime.InteropServices.Marshal]::SizeOf($header))
[Audio]::waveInAddBuffer($hWaveIn, [ref]$header, [System.Runtime.InteropServices.Marshal]::SizeOf($header))
[Audio]::waveInStart($hWaveIn)

$process = Start-Process ncat -ArgumentList "localhost", "43007" -RedirectStandardInput -NoNewWindow -PassThru

while ($true) {
    Start-Sleep -Milliseconds 1000
    $bytes = New-Object byte[] $bufferSize
    [System.Runtime.InteropServices.Marshal]::Copy($buffer, $bytes, 0, $bufferSize)
    $process.StandardInput.BaseStream.Write($bytes, 0, $bufferSize)
    [Audio]::waveInAddBuffer($hWaveIn, [ref]$header, [System.Runtime.InteropServices.Marshal]::SizeOf($header))
}