import asyncio
import httpx
from livekit import rtc

async def main():
    # 1. Create a call
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:8000/calls", json={"agent_id": "10125590effe439c"})
        assert r.status_code == 201, f"Failed to create call: {r.text}"
        data = r.json()
        call_id = data["id"]
        token = data["token"]
        ws_url = data["livekit_url"]
        print(f"Created call {call_id}")

    room = rtc.Room()

    @room.on("track_subscribed")
    def on_track(track, publication, participant):
        print(f"Customer received track: kind={track.kind} from={participant.identity}")

    @room.on("data_received")
    def on_data(packet):
        print(f"Customer received data: topic={packet.topic} data={packet.data.decode('utf-8', errors='ignore')}")

    print(f"Connecting customer to {ws_url}...")
    await room.connect(ws_url, token)
    print("Customer connected! Waiting 10s for agent to enter, start session, and deliver greeting...")
    await asyncio.sleep(10)

    print("Disconnecting customer...")
    await room.disconnect()
    print("Test finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())
