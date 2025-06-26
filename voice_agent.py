# voice_agent.py
from openai.types.beta.realtime.session import InputAudioTranscription
from dotenv import load_dotenv
from prompts import INSTRUCTIONS, LOOKUP_PHONE_MESSAGE
from cava_api import Assistant

from livekit import agents
from livekit.agents import AgentSession, RoomInputOptions
# v1.x renamed ChatImage → ImageContent
from livekit.agents.llm.chat_context import ChatMessage, ImageContent  # :contentReference[oaicite:0]{index=0}

from livekit.plugins import openai, noise_cancellation

load_dotenv()

def find_customer_profile(session: AgentSession, content: str):
    # Inject a system prompt to look up the customer by phone
    session.chat_ctx.append(text=LOOKUP_PHONE_MESSAGE(content), role="system")
    return session.generate_reply()

def handle_customer_query(session: AgentSession, content: str):
    # Append the user's query and generate a response
    session.chat_ctx.append(text=content, role="user")
    return session.generate_reply()

async def start_conversation(ctx: agents.JobContext):
    # First, establish the websocket connection
    await ctx.connect()

    # Create the AgentSession with your LLM model
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="shimmer",
            temperature=0.8,
             input_audio_transcription=InputAudioTranscription(
                model="gpt-4o-transcribe",
                language="en",
                prompt=(
                    "Please enunciate first names and phone-number digits clearly, "
                    "one digit at a time."
                )
            )
        )
    )

    # Register a handler for committed user speech
    def on_user_speech_committed(msg: ChatMessage):
        # Flatten mixed text/image payloads
        content = msg.content
        if isinstance(content, list):
            content = "\n".join(
                "[image]" if isinstance(item, ImageContent) else item
                for item in content
            )

        # Branch based on whether we've already looked up the customer
        if Assistant.has_customer():
            return handle_customer_query(session, content)
        else:
            return find_customer_profile(session, content)

    # Hook into the built-in event name directly
    session.on("user_speech_committed", on_user_speech_committed)

    # Start the voice session in the given room
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Kick off the first assistant response
    await session.generate_reply(instructions=INSTRUCTIONS)

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=start_conversation)
    )
