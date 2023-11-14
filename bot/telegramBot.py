from logs.logging import logger
import os
from typing import Final
import random

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext,
)
import asyncio

from .utils import transcribe_voice_message
from .chat_gpt import respond_to_user

# List of possible initial questions
initial_questions = [
    "What's your favorite English word?",
    "Tell me about your day in English.",
    "Can you describe your favorite place using English?",
    "Share a fun fact in English.",
]

# Load environment variables from the specified path
load_dotenv()


class TelegramBot:
    def __init__(self):
        self.TOKEN: Final = os.getenv("TELEGRAM_BOT_TOKEN")
        self.BOT_USERNAME: Final = os.getenv("BOT_NAME")
        # Dictionary to store user choices
        self.user_choices = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # Create a list of button rows
            keyboard = [
                [InlineKeyboardButton("Text", callback_data="text")],
                [InlineKeyboardButton("Voice", callback_data="voice")],
            ]

            user = update.message.from_user
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                self.greet_user(user.first_name),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

        except Exception as e:
            logger.error(f"Error in start_command: {str(e)}")

    # Define a function to handle the user's choice
    async def handle_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print('running handle_choice')
        try:
            user_id = update.effective_user.id
            user_name = update.effective_user.first_name
            print(f'user_name: {user_name}')

            # Check if the user has already made a choice
            if user_id in self.user_choices:
                user_choice = self.user_choices[user_id]
                await update.callback_query.message.reply_text(
                    f"You have already chosen: {user_choice}. Please start a new conversation to choose again."
                )
                return  # Exit the method

            user_choice = update.callback_query.data
            self.user_choices[user_id] = user_choice  # Store the user's choice
            print(f'user_choice: {user_choice}')

            if user_choice == "text" or user_choice == "voice":
                await update.callback_query.message.reply_text(f"Great! You chose {user_choice} messages.")
                first_question = await self.ask_first_question(user_name)
                print(f'first_question: {first_question}')
                await update.callback_query.message.reply_text(first_question)

        except Exception as e:
            logger.error(f"Error in handle_choice: {str(e)}")

    # Define a callback query handler for the button
    async def lesson_button_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        try:
            await update.callback_query.message.reply_text("How are you? ")
        except Exception as e:
            logger.error(f"Error in lesson_button_callback: {str(e)}")

    def handle_text_response(self, text: str) -> str:
        try:
            response = respond_to_user(text)
            return response

        except Exception as e:
            logger.error(f"Error in handle_text_response: {str(e)}")
            print(f"Error in handle_text_response: {str(e)}")

    def handle_voice_response(self, text: str) -> str:
        try:
            # TODO: have to implement
            pass

        except Exception as e:
            logger.error(f"Error in handle_voice_response: {str(e)}")
            print(f"Error in handle_voice_response: {str(e)}")

    async def handle_audio(self, update: Update, context: ContextTypes):
        try:
            # Check if the message contains audio
            if update.message.voice:
                audio_file_id = update.message.voice.file_id

                # Define the directory where you want to save voice messages
                voice_messages_dir = "bot/voice_messages"
                # Check if the directory exists, and if not, create it
                if not os.path.exists(voice_messages_dir):
                    os.makedirs(voice_messages_dir)

                # Use the bot's 'getFile' method to get the file path
                file = await context.bot.get_file(audio_file_id)
                file_path = os.path.join(voice_messages_dir, f"{audio_file_id}.ogg")

                # Download the audio to the file
                await file.download_to_drive(file_path)

                transcription = transcribe_voice_message(audio_file_id)

                response: str = self.handle_voice_response(transcription)

                print("Bot: ", response)
                await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error in handle_audio: {str(e)}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print('handle_message')
        try:
            text: str = update.message.text
            user_id = update.effective_user.id
            user_name = update.effective_user.first_name
            logger.info(f"User [{user_name}]: {text}")
            print(f"User [{user_name}]:", text)

            # Retrieve user choice from the dictionary
            user_choice = self.user_choices.get(user_id)

            if user_choice == "text":
                logger.info("Text Mode")
                response: str = self.handle_text_response(text)
            elif user_choice == "voice":
                logger.info("Voice Mode")
                # TODO: have to replace the handle_text_response function with handle_voice_response that will handle the voice mode
                response: str = self.handle_text_response(text)
            else:
                logger.warning("User has not made a choice yet")
                # Handle the case when the user hasn't made a choice yet
                response = "Please choose 'Text' or 'Voice' first."

            print("Bot:", response)
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error in handle_message: {str(e)}")

    def greet_user(self, user_name: str) -> str:
        return f"<b>Hi {user_name}!</b>\n"\
            "I am your English Tutor ChatBot.\n"\
            "I'm here to help you improve your spoken English.\n"\
            "I will correct your mistakes and ask you questions to practice.\n\n"\
            "<i>How would you like to communicate with me?</i>"

    async def ask_first_question(self, user_name: str) -> str:
        print('ask_first_question is running')
        # Randomly select an initial question
        random_question = random.choice(initial_questions)
        introduction = f"Let's start with a question: {random_question}"
        return introduction

    async def error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logger.error(f"Update {update} caused error {context.error}")
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")

    def run_bot(self):
        logger.info("Starting bot...")
        print("Starting bot...")
        app = ApplicationBuilder().token(self.TOKEN).build()

        # Commands
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CallbackQueryHandler(self.handle_choice, pattern="text"))
        app.add_handler(CallbackQueryHandler(self.handle_choice, pattern="voice"))

        # # Messages
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.VOICE, self.handle_audio))
        # Register the callback query handler
        app.add_handler(
            CallbackQueryHandler(
                self.ask_first_question, pattern="ask_first_question"
            )
        )
     
        # Errors
        app.add_error_handler(self.error)

        app.run_polling(poll_interval=3)
