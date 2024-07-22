import pyaudio
import socket
import numpy as np
import librosa
import threading
import wave

# Audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 2  # VB-Cable typically uses stereo
RATE = 44100  # VB-Cable typically uses 44.1kHz
CHUNK = 4410  # 0.1 second of audio at 44.1kHz

# Target parameters
TARGET_CHANNELS = 1
TARGET_RATE = 16000

# Network parameters
HOST = 'localhost'
PORT = 43007

# Output file for server responses
OUTPUT_FILE = "server_responses.txt"

def find_vb_cable_device():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if 'CABLE Output' in dev['name']:
            return i
    return None

def receive_server_responses(sock):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        buffer = b''
        while True:
            try:
                data = sock.recv(1024)
                if not data:
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    response = line.rstrip(b'\x00').decode('utf-8', errors='ignore').strip()
                    if response and response != "nul":
                        print(f"Received from server: {response}")
                        f.write(response + '\n')
                        f.flush()
            except Exception as e:
                print(f"Error receiving data: {e}")
                break

def main():
    p = pyaudio.PyAudio()
    
    device_index = find_vb_cable_device()
    if device_index is None:
        print("VB-Cable Output device not found. Make sure it's installed and enabled.")
        return

    # Open the audio stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=CHUNK)

    print("Capturing system audio...")

    # Create a socket and connect to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Start a thread to receive server responses
    receive_thread = threading.Thread(target=receive_server_responses, args=(sock,))
    receive_thread.start()

    try:
        while True:
            # Read audio data
            data = stream.read(CHUNK)
            
            # Convert to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Reshape to stereo
            audio_data = audio_data.reshape(-1, CHANNELS)
            
            # Convert to float32 for librosa
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Resample using librosa
            resampled = librosa.resample(audio_float.T, orig_sr=RATE, target_sr=TARGET_RATE)
            
            # Mix down to mono
            mono = resampled.mean(axis=0)
            
            # Convert back to int16
            mono_int16 = (mono * 32767).astype(np.int16)
            
            # Send the resampled data to the server
            sock.sendall(mono_int16.tobytes())
    except KeyboardInterrupt:
        print("Stopped capturing")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up
        stream.stop_stream()
        stream.close()
        p.terminate()
        sock.close()
        receive_thread.join()

if __name__ == "__main__":
    main()