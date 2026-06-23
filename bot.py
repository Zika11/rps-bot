async def channel_round(context: ContextTypes.DEFAULT_TYPE):
    channel_id = int(context.job.chat_id)
    if channel_id not in channel_jobs:
        return

    game = channel_games.get(channel_id)
    if game and datetime.now() - game["created"] > timedelta(seconds=90):
        await cancel_channel_game(channel_id, context)

    if channel_id in channel_games:
        return

    try:
        msg = await context.bot.send_message(
            channel_id,
            "🎮 *جولة جديدة بين عضوين!* أول واحد يضغط هيبقى اللاعب الأول 👇",
            parse_mode="Markdown",
            reply_markup=channel_keyboard(channel_id)
        )
        channel_games[channel_id] = {
            "player1": None, "choice1": None,
            "player2": None, "choice2": None,
            "message_id": msg.message_id,
            "created": datetime.now()
        }
        channel_last_play[channel_id] = datetime.now()
    except (tg_error.Forbidden, tg_error.BadRequest, tg_error.ChatNotFound):
        # فشل الإرسال بسبب الصلاحيات – نوقف المهمة ونخلي المسؤول يعرف
        await stop_channel_job(channel_id, context)
        # نحاول إرسال رسالة أخيرة للمسؤول (قد تفشل أيضاً)
        try:
            await context.bot.send_message(
                channel_id,
                "⚠️ تم إيقاف اللعب التلقائي بسبب عدم وجود صلاحيات كافية للبوت.\n"
                "تأكد من أن البوت Admin ولديه صلاحية إرسال الرسائل، ثم أعد تفعيله بـ /activate."
            )
        except:
            pass
    except Exception as e:
        # خطأ آخر مؤقت – نتجاوز هذه الدورة
        print(f"خطأ مؤقت في القناة {channel_id}: {e}")
