from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from yt_dlp import YoutubeDL
from pyrogram import Client
import os
import telegram.error

# توکن ربات خود را اینجا قرار دهید
TOKEN = 'token bot'

# ایجاد کلاینت Pyrogram برای ربات (خارج از تابع)
app = Client(
    name="usernamebot",
    bot_token=TOKEN,
    api_id='api_id',
    api_hash="api_hash"
    )

# تنظیمات yt-dlp برای دانلود ویدئو
ydl_opts_video = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': '%(title)s.%(ext)s',
    'merge_output_format': 'mp4',
    'cookiefile': 'cookies.txt',
    'ignoreerrors': True,  # اضافه کردن این خط برای نادیده گرفتن خطاها در پلی‌لیست
    'retries': 10,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
}

ydl_opts_playlist = {
    'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',  # حداکثر کیفیت 720p و فقط mp4
    'outtmpl': '%(playlist_index)s - %(title)s.%(ext)s',  # نام فایل خروجی
    'ignoreerrors': True,  # خطای ویدیوهای ناموفق را نادیده می‌گیرد
    'cookiefile': 'cookies.txt',
    'retries': 10,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    context.user_data[user_id] = {'is_downloading': False}
    await update.message.reply_text('سلام! برای دانلود ویدئو از دستور /download_video و برای دانلود پلی‌لیست از دستور /download_playlist استفاده کنید.')

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if context.user_data[user_id]['is_downloading']:
        await update.message.reply_text('شما در حال حاضر مشغول دانلود هستید. لطفاً صبر کنید.')
        return

    context.user_data[user_id]['is_downloading'] = True
    await update.message.reply_text('لطفاً لینک ویدئو یوتیوب را ارسال کنید.')

async def download_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if context.user_data[user_id]['is_downloading']:
        await update.message.reply_text('شما در حال حاضر مشغول دانلود هستید. لطفاً صبر کنید.')
        return

    context.user_data[user_id]['is_downloading'] = True
    await update.message.reply_text('لطفاً لینک پلی‌لیست یوتیوب را ارسال کنید.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if not context.user_data[user_id]['is_downloading']:
        await update.message.reply_text('لطفاً از دستور /download_video یا /download_playlist استفاده کنید.')
        return

    url = update.message.text
    if 'youtube.com/playlist' in url:
        await download_playlist_handler(update, context, url)
    else:
        await download_video_handler(update, context, url)

async def download_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    user_id = update.message.from_user.id
    try:
        message = await update.message.reply_text('در حال یافتن کیفیت های موجود...')
        title, video_info = get_video_info(url)
        if not title or not video_info:
            await update.message.reply_text('خطا: اطلاعات ویدئو یافت نشد. لطفاً لینک را بررسی کنید.')
            return

        keyboard = []
        for info in video_info:
            button_text = f"{info['resolution']} ({info['filesize']} MB)"
            callback_data = f"download_video_{info['format_id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.edit_text(f'ویدیو: {title}\nلطفاً کیفیت مورد نظر را انتخاب کنید:', reply_markup=reply_markup)
        context.user_data['url'] = url
    except Exception as e:
        await update.message.reply_text(f'خطا: {e}')
        context.user_data[user_id]['is_downloading'] = False

# تابع دانلود پلی‌لیست
def download_playlist_videos(url):
    ydl_opts_playlist['ignoreerrors'] = True  # اطمینان از فعال بودن
    with YoutubeDL(ydl_opts_playlist) as ydl:
        info = ydl.extract_info(url, download=True)
        
    # مسیر پوشه کنار پروژه
    current_directory = os.getcwd()

    # پیدا کردن فایل‌های با پسوند .mp4
    mp4_files = [f for f in os.listdir(current_directory) if f.endswith('.mp4') and os.path.isfile(os.path.join(current_directory, f))]
    
    return mp4_files

async def send_playlist(update):
    # مسیر پوشه کنار پروژه
    current_directory = os.getcwd()

    # پیدا کردن فایل‌های با پسوند .mp4
    videos = [f for f in os.listdir(current_directory) if f.endswith('.mp4') and os.path.isfile(os.path.join(current_directory, f))]
    
    async with app:
        for video in videos:
            file_path = os.path.join(os.getcwd(), video)  # مسیر کامل فایل
            if os.path.exists(file_path):
                await send_video_as_whole(update, file_path)
                os.remove(file_path)  # حذف فایل پس از ارسال
            else:
                await update.message.reply_text(f"فایل {video} یافت نشد.")
    
async def download_playlist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    user_id = update.message.from_user.id
    try:
        # دانلود پلی‌لیست
        await update.message.reply_text("در حال دانلود پلی‌لیست...")

        videos = download_playlist_videos(url)
        
        await update.message.reply_text("در حال آپلود پلی‌لیست...")

        # ارسال ویدئوها به تلگرام
        await send_playlist(update)

        await update.message.reply_text('دانلود و ارسال ویدئوهای پلی‌لیست به پایان رسید.')
    except Exception as e:
        await update.message.reply_text(f'خطا: {e}')
        await send_playlist(update)
        
    finally:
        await send_playlist(update)
        context.user_data[user_id]['is_downloading'] = False

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        if data.startswith('download_video'):
            format_id = data.split('_')[2]
            url = context.user_data['url']
            await download_video_with_format(query, url, format_id, context, user_id)
        elif data.startswith('select_video'):
            video_index = int(data.split('_')[2])
            video_url = context.user_data['playlist_urls'][video_index]
            context.user_data['selected_video_url'] = video_url
            await select_video_quality(query, video_url, context)
        elif data.startswith('download_playlist_video'):
            format_id = data.split('_')[3]
            video_url = context.user_data['selected_video_url']
            await download_video_with_format(query, video_url, format_id, context, user_id)
    except telegram.error.TimedOut:
        await query.edit_message_text("خطا: زمان درخواست به پایان رسید. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        await query.edit_message_text(f"خطا: {e}")

async def select_video_quality(query, video_url, context):
    try:
        title, video_info = get_video_info(video_url)
        if not title or not video_info:
            await query.edit_message_text('خطا: اطلاعات ویدئو یافت نشد. لطفاً لینک را بررسی کنید.')
            return

        keyboard = []
        for info in video_info:
            button_text = f"{info['resolution']} ({info['filesize']} MB)"
            callback_data = f"download_playlist_video_{info['format_id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f'ویدیو: {title}\nلطفاً کیفیت مورد نظر را انتخاب کنید:', reply_markup=reply_markup)
    except Exception as e:
        await query.edit_message_text(f'خطا: {e}')

async def download_video_with_format(query, url, format_id, context, user_id):
    filename = None
    try:
        ydl_opts_video['format'] = format_id
        await query.edit_message_text('در حال دانلود...')
        with YoutubeDL(ydl_opts_video) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            await query.edit_message_text('در حال آپلود...')
            await send_video_as_whole(query, filename)  # استفاده از await
    except Exception as e:
        await query.edit_message_text(f'خطا در دانلود یا آپلود ویدئو: {e}')
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)
        context.user_data[user_id]['is_downloading'] = False

async def send_video_as_whole(update, filename):
    try:
        # بررسی وجود فایل
        if not os.path.exists(filename):
            await update.message.reply_text('خطا: فایل یافت نشد.')
            return

        # بررسی اندازه فایل
        file_size = os.path.getsize(filename)
        if file_size > 2000 * 1024 * 1024:  # اگر فایل بزرگ‌تر از 2000 مگابایت باشد
            await update.message.reply_text('خطا: اندازه فایل بیشتر از 2000 مگابایت است و نمی‌توان آن را ارسال کرد.')
            return

        # شروع کلاینت Pyrogram اگر قبلاً شروع نشده است
        if not app.is_connected:
            await app.start()

        # آپلود فایل
        await app.send_video(
            chat_id=update.message.chat.id,
            video=filename,
            caption=os.path.basename(filename),
            supports_streaming=True
        )

    except Exception as e:
        await update.message.reply_text(f'خطا در ارسال ویدئو: {e}')
    finally:
        # توقف کلاینت Pyrogram اگر لازم است
        if app.is_connected:
            await app.stop()

def get_video_info(url):
    try:
        with YoutubeDL(ydl_opts_video) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            video_info = []
            for f in formats:
                if f.get('height'):
                    filesize = f.get('filesize', 0) or 0
                    if filesize > 0:
                        video_info.append({
                            'resolution': f'{f["height"]}p',
                            'filesize': filesize // 1024 // 1024,
                            'format_id': f['format_id'],
                        })
            return info['title'], video_info
    except Exception as e:
        print(f"خطا در دریافت اطلاعات ویدئو: {e}")
        return None, None

def main() -> None:
    application = Application.builder().token(TOKEN).read_timeout(120).connect_timeout(120).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download_video", download_video))
    application.add_handler(CommandHandler("download_playlist", download_playlist))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.run_polling()

if __name__ == '__main__':
    main()