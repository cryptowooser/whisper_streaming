import pyaudio

def list_audio_devices():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        print(f"Index {i}: {dev['name']}, Max Input Channels: {dev['maxInputChannels']}")
    p.terminate()

if __name__ == "__main__":
    list_audio_devices()