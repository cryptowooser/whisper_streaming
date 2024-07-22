import pyaudio
import socket
import numpy as np
import librosa
import threading
import streamlit as st
import queue
import time
import re
from translation_module import translate_string

# Audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 4410

# Target parameters
TARGET_CHANNELS = 1
TARGET_RATE = 16000

# Network parameters
HOST = 'localhost'

def find_vb_cable_device():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if 'CABLE Output' in dev['name']:
            return i
    return None

def receive_server_responses(sock, output_queue, stop_event):
    buffer = b''
    while not stop_event.is_set():
        try:
            data = sock.recv(1024)
            if not data:
                break
            buffer += data
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                response = line.decode('utf-8', errors='ignore').replace('\x00', '').strip()
                if response and re.search(r'\d', response):
                    parts = response.split(' ', 2)
                    if len(parts) > 2:
                        response = parts[2]
                    output_queue.put(f"{response}")
        except Exception as e:
            output_queue.put(f"Error receiving data: {e}")
            break

def audio_streaming(stop_event, output_queue, port):
    p = pyaudio.PyAudio()
    
    device_index = find_vb_cable_device()
    if device_index is None:
        output_queue.put("VB-Cable Output device not found. Make sure it's installed and enabled.")
        return

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=CHUNK)

    output_queue.put("Capturing system audio...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, port))
        output_queue.put("Connected to server.")

        receive_thread = threading.Thread(target=receive_server_responses, args=(sock, output_queue, stop_event))
        receive_thread.start()

        while not stop_event.is_set():
            data = stream.read(CHUNK)
            audio_data = np.frombuffer(data, dtype=np.int16).reshape(-1, CHANNELS)
            audio_float = audio_data.astype(np.float32) / 32768.0
            resampled = librosa.resample(audio_float.T, orig_sr=RATE, target_sr=TARGET_RATE)
            mono = resampled.mean(axis=0)
            mono_int16 = (mono * 32767).astype(np.int16)
            sock.sendall(mono_int16.tobytes())
    except Exception as e:
        output_queue.put(f"An error occurred: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        sock.close()
        output_queue.put("Disconnected from server.")
        stop_event.set()

def main():
    st.title("Real-time BiLingual Audio Streaming with Whisper")
    
    # Dropdown for language selection
    port = st.selectbox('Select Language', ('English - 43007', 'Japanese - 43008'), format_func=lambda x: x.split(' - ')[0])
    port = int(port.split(' - ')[1])

    if 'stop_event' not in st.session_state:
        st.session_state.stop_event = threading.Event()
    if 'output_queue' not in st.session_state:
        st.session_state.output_queue = queue.Queue()
    if 'streaming' not in st.session_state:
        st.session_state.streaming = False
    if 'output_text' not in st.session_state:
        st.session_state.output_text = ""

    # Display current state
    state_text = "Stopped" if not st.session_state.streaming else "Streaming"
    st.write(f"Current State: {state_text}")

    col1, col2, col3 = st.columns(3)
    with col1:
        start_button = st.button("Start Streaming")
    with col2:
        stop_button = st.button("Stop Streaming")
    with col3:
        clear_button = st.button("Clear Output")

    if start_button and not st.session_state.streaming:
        st.session_state.streaming = True
        st.session_state.stop_event.clear()
        audio_thread = threading.Thread(target=audio_streaming, args=(st.session_state.stop_event, st.session_state.output_queue, port))
        audio_thread.start()

    if stop_button and st.session_state.streaming:
        st.session_state.streaming = False
        st.session_state.stop_event.set()

    if clear_button:
        st.session_state.output_text = ""

    output_area = st.empty()

    while True:
        while not st.session_state.output_queue.empty():
            try:
                message = st.session_state.output_queue.get_nowait()
                st.session_state.output_text += message + "\n"
            except queue.Empty:
                break

        output_area.text_area("Output", value=st.session_state.output_text, height=300)
        time.sleep(1)
        st.rerun()

if __name__ == "__main__":
    main()
