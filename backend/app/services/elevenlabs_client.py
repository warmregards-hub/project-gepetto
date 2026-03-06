class ElevenLabsClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def generate_speech(self, text: str, voice_id: str):
        # Phase 3 implementation
        print(f"[Project Gepetto Voice] Generating TTS for: {text}")
        return b"dummy_audio_bytes"
