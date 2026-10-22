import asyncio
import io
import os
import wave
import httpx
from dotenv import load_dotenv
from livekit import rtc

load_dotenv()
DEEPGRAM_KEY = os.getenv("DEEPGRAM_API_KEY", "")

async def generate_speech_wav(text: str) -> bytes:
    """Use Deepgram TTS to produce 16kHz PCM WAV for the simulated customer."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.deepgram.com/v1/speak?model=aura-2-thalia-en&encoding=linear16&sample_rate=16000",
            headers={"Authorization": f"Token {DEEPGRAM_KEY}", "Content-Type": "application/json"},
            json={"text": text},
            timeout=15.0,
        )
        assert r.status_code == 200, f"TTS error: {r.text}"
        return r.content

async def main():
    print("1. Generating simulated customer speech ('What products do you offer?')...")
    wav_bytes = await generate_speech_wav("What products do you offer?")
    
    # Read raw 16kHz mono PCM frames from WAV
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        raw_pcm = wf.readframes(wf.getnframes())
    print(f"Customer speech generated: {len(raw_pcm)} bytes at {sample_rate}Hz, {channels}ch")

    # 2. Create a call
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:8000/calls", json={"agent_id": "10125590effe439c"})
        assert r.status_code == 201
        data = r.json()
        call_id = data["id"]
        token = data["token"]
        ws_url = data["livekit_url"]
        print(f"2. Created call {call_id}")

    room = rtc.Room()
    received_transcripts = []

    @room.on("data_received")
    def on_data(packet):
        if packet.topic == "transcript":
            msg = packet.data.decode("utf-8", errors="ignore")
            received_transcripts.append(msg)
            print(f"LIVE DATA TRANSCRIPT: {msg}")

    @room.on("track_subscribed")
    def on_track(track, publication, participant):
        print(f"Customer received agent track: kind={track.kind} from={participant.identity}")

    print(f"3. Connecting customer to {ws_url}...")
    await room.connect(ws_url, token)
    print("Customer connected!")

    # 4. Set up customer microphone audio track
    source = rtc.AudioSource(sample_rate=sample_rate, num_channels=channels)
    track = rtc.LocalAudioTrack.create_audio_track("customer_mic", source)
    options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    await room.local_participant.publish_track(track, options)
    print("Customer microphone published!")

    # Wait 8s for the agent's greeting to finish
    print("Waiting 8s for agent greeting...")
    await asyncio.sleep(8)

    # 5. Send customer speech frames into microphone
    print("Speaking customer question into microphone: 'What products do you offer?'...")
    frame_size = int(sample_rate * channels * 2 * 0.02)  # 20ms frames
    for i in range(0, len(raw_pcm), frame_size):
        chunk = raw_pcm[i : i + frame_size]
        if len(chunk) < frame_size:
            chunk = chunk + b"\x00" * (frame_size - len(chunk))
        frame = rtc.AudioFrame(
            data=chunk,
            sample_rate=sample_rate,
            num_channels=channels,
            samples_per_channel=len(chunk) // (2 * channels),
        )
        await source.capture_frame(frame)
        await asyncio.sleep(0.02)

    # Push 1s of silence so VAD endpoints promptly
    silence = b"\x00" * frame_size
    for _ in range(50):
        frame = rtc.AudioFrame(
            data=silence,
            sample_rate=sample_rate,
            num_channels=channels,
            samples_per_channel=len(silence) // (2 * channels),
        )
        await source.capture_frame(frame)
        await asyncio.sleep(0.02)

    print("Customer finished speaking! Waiting 12s for STT, LLM response, and agent speech...")
    await asyncio.sleep(12)

    print("Disconnecting customer...")
    await room.disconnect()
    print("Customer disconnected.")

    # 6. Verify conversation in database
    async with httpx.AsyncClient() as client:
        r = await client.get(f"http://localhost:8000/calls/{call_id}/transcript")
        print("\n=== FINAL PERSISTED TRANSCRIPT ===")
        for turn in r.json():
            print(f"[{turn['speaker'].upper()}]: {turn['text']}")

        r_comp = await client.get(f"http://localhost:8000/calls/{call_id}")
        print("\n=== COMPLIANCE RESULTS ===")
        for comp in r_comp.json().get("compliance", []):
            print(f"Rule: {comp['rule']} -> {comp['status']} ({comp['detail']})")

if __name__ == "__main__":
    asyncio.run(main())
