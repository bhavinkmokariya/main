import streamlit as st
import wikipedia
from huggingface_hub import InferenceClient
import io
import os
import subprocess
import toml

# Load Hugging Face API key from secrets.toml
api_key = st.secrets["huggingface_api_key"]
client = InferenceClient(token=api_key)


# Function to fetch topic details from Wikipedia
def fetch_topic_details(prompt):
    try:
        summary = wikipedia.summary(prompt, sentences=5)
        return summary
    except Exception as e:
        return f"Error fetching details: {str(e)}"


# Function to generate images based on prompt using Hugging Face API
def generate_images(prompt):
    image_data_list = []
    try:
        for i in range(4):  # Generate 4 images
            image_data = client.text_to_image(prompt, model="OFA-Sys/small-stable-diffusion-v0")
            image_data_list.append(io.BytesIO(image_data))  # Store image data in memory
    except Exception as e:
        st.error(f"Error generating images: {str(e)}")
    return image_data_list


# Function to generate audio narration of the topic details using Hugging Face API
def generate_audio(text):
    try:
        audio_data = client.text_to_speech(text, model="facebook/mms-tts-eng")
        return io.BytesIO(audio_data)  # Store audio data in memory
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        return None


# Function to assemble video in memory using FFmpeg subprocess
def assemble_video(images, audio_stream):
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",  # Overwrite existing files (doesn't apply here since we use streams)
        "-f", "image2pipe",
        "-i", "-",  # Input images from pipe
        "-i", "-",  # Input audio from pipe
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-f", "mp4",
        "-"
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    try:
        # Write images to FFmpeg's stdin
        for image_data in images:
            process.stdin.write(image_data.getvalue())

        # Write audio to FFmpeg's stdin if available
        if audio_stream:
            process.stdin.write(audio_stream.getvalue())

        process.stdin.close()

        return process.stdout.read()  # Return video stream directly

    except Exception as e:
        st.error(f"Error assembling video: {str(e)}")
        return None


# Streamlit UI setup
st.title("Text-to-Video Chatbot")

user_input = st.text_input("Enter your prompt:")

if st.button("Generate Video"):
    if user_input:
        with st.spinner("Generating video..."):
            topic_details = fetch_topic_details(user_input)
            st.write("Fetched Details:")
            st.write(topic_details)

            images = generate_images(topic_details)
            if not images:
                st.error("Failed to generate images.")
                st.stop()

            audio_stream = generate_audio(topic_details)
            if not audio_stream:
                st.error("Failed to generate audio.")
                st.stop()

            video_stream = assemble_video(images, audio_stream)
            if video_stream:
                st.video(video_stream)  # Display the generated video
            else:
                st.error("Failed to assemble video.")
