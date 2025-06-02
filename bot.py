import logging
import os
from config import TELEGRAM_BOT_TOKEN, YANDEX_MUSIC_TOKEN
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from yandex_music import Client

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class YandexMusicBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.yandex_token = YANDEX_MUSIC_TOKEN
        self.yandex_client = Client(self.yandex_token).init()

    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        await update.message.reply_text(
            f"Привет, {user.first_name if user else 'пользователь'}! Я бот для работы с Яндекс.Музыкой.\n"
            "Доступные команды:\n"
            "/search <название> - Поиск треков\n"
            "/artist <имя> - Информация об исполнителе\n"
            "/playlists <запрос> - Поиск плейлистов\n"
            "/lyrics <исполнитель - трек> - Получить текст песни"
        )
        await self.log_interaction(update, "start command")

    async def search_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Поиск треков по запросу"""
        query = ' '.join(context.args) if context.args else ''
        if not query:
            await update.message.reply_text("Пожалуйста, укажите название трека.")
            return

        try:
            search_result = self.yandex_client.search(query)
            tracks = search_result.tracks

            if not tracks or not tracks.results:
                await update.message.reply_text("Ничего не найдено.")
                return

            response = "Результаты поиска:\n"
            for i, track in enumerate(tracks.results[:5], 1):
                artists = ", ".join(
                    artist.name for artist in track.artists) if track.artists else "Неизвестный исполнитель"
                response += f"{i}. {artists} - {track.title}\n"

            await update.message.reply_text(response)
            await self.log_interaction(update, f"search tracks: {query}")

        except Exception as e:
            logger.error(f"Error in search_tracks: {e}")
            await update.message.reply_text("Произошла ошибка при поиске.")
            await self.log_interaction(update, f"search tracks error: {e}")

    async def get_artist_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Получение информации об исполнителе"""
        artist_name = ' '.join(context.args) if context.args else ''
        if not artist_name:
            await update.message.reply_text("Пожалуйста, укажите имя исполнителя.")
            return

        try:
            search_result = self.yandex_client.search(artist_name)
            artist = search_result.artists.results[
                0] if search_result.artists and search_result.artists.results else None

            if not artist:
                await update.message.reply_text("Исполнитель не найден.")
                return

            info = f"Информация об исполнителе {artist.name if hasattr(artist, 'name') else 'Неизвестный исполнитель'}:\n"

            if hasattr(artist, 'genres') and artist.genres:
                info += f"Жанры: {', '.join(artist.genres)}\n"
            else:
                info += "Жанры: не указаны\n"

            if hasattr(artist, 'counts'):
                tracks_count = artist.counts.tracks if hasattr(artist.counts, 'tracks') else 'неизвестно'
                albums_count = artist.counts.albums if hasattr(artist.counts, 'albums') else 'неизвестно'
                info += f"Количество треков: {tracks_count}\n"
                info += f"Количество альбомов: {albums_count}\n"

            await update.message.reply_text(info)
            await self.log_interaction(update, f"artist info: {artist_name}")

        except Exception as e:
            logger.error(f"Error in get_artist_info: {e}")
            await update.message.reply_text("Произошла ошибка при получении информации.")
            await self.log_interaction(update, f"artist info error: {e}")

    async def search_playlists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Поиск плейлистов по запросу"""
        query = ' '.join(context.args) if context.args else ''
        if not query:
            await update.message.reply_text("Пожалуйста, укажите запрос для поиска плейлистов.")
            return

        try:
            search_result = self.yandex_client.search(query, type_='playlist')
            playlists = search_result.playlists

            if not playlists or not playlists.results:
                await update.message.reply_text("Плейлисты не найдены.")
                return

            response = "Найденные плейлисты:\n"
            for i, playlist in enumerate(playlists.results[:5], 1):
                title = playlist.title if hasattr(playlist, 'title') else 'Без названия'
                track_count = playlist.track_count if hasattr(playlist, 'track_count') else '?'
                owner_name = playlist.owner.name if hasattr(playlist.owner, 'name') else 'Неизвестный создатель'

                response += f"{i}. {title} ({track_count} треков)\n"
                response += f"   Создатель: {owner_name}\n"

            await update.message.reply_text(response)
            await self.log_interaction(update, f"search playlists: {query}")

        except Exception as e:
            logger.error(f"Error in search_playlists: {e}")
            await update.message.reply_text("Произошла ошибка при поиске плейлистов.")
            await self.log_interaction(update, f"search playlists error: {e}")

    async def get_lyrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Получение текста песни"""
        query = ' '.join(context.args) if context.args else ''
        if not query:
            await update.message.reply_text("Пожалуйста, укажите исполнителя и название трека.")
            return

        try:
            if ' - ' in query:
                artist, track = query.split(' - ', 1)
            else:
                artist, track = query, ""

            search_result = self.yandex_client.search(f"{artist} {track}")
            tracks = search_result.tracks

            if not tracks or not tracks.results:
                await update.message.reply_text("Трек не найден.")
                return

            lyrics_info = tracks.results[0].get_lyrics()
            if not lyrics_info:
                await update.message.reply_text("Текст песни не найден.")
                return

            lyrics = lyrics_info.fetch_lyrics()
            await update.message.reply_text(f"Текст песни {artist} - {track}:\n\n{lyrics}")
            await self.log_interaction(update, f"get lyrics: {query}")

        except Exception as e:
            logger.error(f"Error in get_lyrics: {e}")
            await update.message.reply_text("Произошла ошибка при получении текста песни.")
            await self.log_interaction(update, f"get lyrics error: {e}")

    @staticmethod
    async def log_interaction(update: Update, message: str) -> None:
        """Логирование взаимодействий с пользователем"""
        user = update.effective_user
        if not user:
            return

        user_id = user.id
        log_file = f"logs/{user_id}.log"

        os.makedirs("logs", exist_ok=True)

        with open(log_file, "a", encoding="utf-8") as f:
            full_name = user.full_name if hasattr(user, 'full_name') else 'Неизвестный пользователь'
            timestamp = update.message.date if update.message and hasattr(update.message, 'date') else 'N/A'

            f.write(f"User: {full_name} ({user_id})\n")
            f.write(f"Message: {message}\n")
            f.write(f"Timestamp: {timestamp}\n\n")

    async def log_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Логирование обычных сообщений пользователя"""
        message_text = update.message.text if update.message and hasattr(update.message, 'text') else 'N/A'
        await self.log_interaction(update, f"User message: {message_text}")

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.token).build()

        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("search", self.search_tracks))
        application.add_handler(CommandHandler("artist", self.get_artist_info))
        application.add_handler(CommandHandler("playlists", self.search_playlists))
        application.add_handler(CommandHandler("lyrics", self.get_lyrics))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.log_message))

        application.run_polling()

if __name__ == '__main__':
    bot = YandexMusicBot()
    bot.run()