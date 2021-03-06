import logging
import requests, json
import os
import random
import psycopg2
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

CHOOSING, CREATE_DECK, CREATE_ANSWERS, CREATE_QUESTIONS, PLAY_DECK, VIEW_ALL_DECKS, VIEW_MY_DECKS, WAITING_FOR_USER_ANS, \
GIVE_USER_QUESTION, LEADERBOARDS, MOTIVATION = range(11)

PORT = int(os.environ.get('PORT', 5000))
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = '1908824393:AAE3SZKfsySMCu-PZQNqtuiy7Xm4GXKEHsM'
reply_keyboard = [['Create Deck', 'Play Deck'],
                  ['View All Decks', 'View My Decks'],
                  ['Leaderboards', 'Motivate Me!']]

markup = ReplyKeyboardMarkup(reply_keyboard)


def generate_random_string():
    deck_token = ''.join(random.choice('0123456789ABCDEF') for i in range(16))
    return deck_token


def database_connection():
    con = psycopg2.connect(user="wphtrnjifgtphq",
                           password="c870974f40f5ca10d7f7abcb6cbc4b89137bc612a516a917784990da74c3bd95",
                           host="ec2-35-174-56-18.compute-1.amazonaws.com",
                           port="5432",
                           database="dac876p6jjg42g")
    return con


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    start_message = "Welcome to Pandamic_Learner Bot! \n\nNeed help? Click /help to see all available commands and what they do."
    update.message.reply_text(start_message, reply_markup=markup)
    return CHOOSING


def help(update, context):
    """Send a message when the command /help is issued."""

    helpMessage = "✨ Commands:\n\n"
    helpMessage += "/start - start using me! 🧸\n\n"
    helpMessage += "Create Deck - create a new deck! ➕ \n"
    helpMessage += "Play deck - let's start learning 📖\n"
    helpMessage += "View All Decks - let's take a peek at everyone's decks 👀 \n"
    helpMessage += "View My Deck - view your own deck 📔\n"
    helpMessage += "Leaderboards - check our how everybody is faring! 🏆 \n"
    helpMessage += "Motivate me - feeling down or unmotivated? Click me to feel better! 💪🏻 \n"
    update.message.reply_text(helpMessage, reply_markup=markup)


def create_deck_message(update, context):
    message = "Want to create a new deck? Please give your new deck a name. \n\n"
    message += "To cancel, type /cancel. Once you are done adding your questions and answers, type /submit."
    update.message.reply_text(message)
    return CREATE_DECK


def create_deck(update, context):
    user_input = update.message.text
    deck_token = generate_random_string()
    context.chat_data["deck_token"] = deck_token
    if user_input == "/cancel":
        cancel(update, context)
        return CHOOSING
    else:
        deck = user_input

        try:
            connection = database_connection()
            cursor = connection.cursor()
            deck_data = (user_input, update.message.from_user.username, deck_token)
            insert_query = """INSERT INTO decks (deck_name, deck_owner, deck_token) VALUES (%s, %s, %s) """
            cursor.execute(insert_query, deck_data)
            connection.commit()
            print("Deck created successfully!")
        except (Exception, psycopg2.Error) as e:  # as error :
            print(format(e))

    cursor.close()
    connection.close()

    reply_keyboard = [['Yes', 'No']]
    update.message.reply_text("Proceed to add questions to your new deck?",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return CREATE_QUESTIONS


def create_questions(update, context):
    user_input = update.message.text
    if user_input == "No":
        cancel(update, context)
        return CHOOSING
    if user_input == "/submit":
        update.message.reply_text("Submitted!")
        return CHOOSING
    else:
        if user_input != "Yes":
            context.chat_data["answer"] = user_input

            try:
                connection = database_connection()
                cursor = connection.cursor()
                questions_data = (
                    context.chat_data["question"], context.chat_data["answer"], context.chat_data["deck_token"])
                insert_query = """INSERT INTO questions (question, answer, deck_token) VALUES (%s, %s, %s) """
                cursor.execute(insert_query, questions_data)
                connection.commit()
                print("Questions and ans created successfully!")

            except (Exception, psycopg2.Error) as e:  # as error :
                print(format(e))

            cursor.close()
            connection.close()

        update.message.reply_text("Please enter your question.")
        return CREATE_ANSWERS


def create_answers(update, context):
    user_input = update.message.text
    context.chat_data["question"] = user_input
    update.message.reply_text("Please enter your answers.")
    if user_input == "/submit":
        update.message.reply_text("Submitted!")
        return CHOOSING
    return CREATE_QUESTIONS


def check_if_token_is_valid(given_deck_token):
    try:
        connection = database_connection()
        cursor = connection.cursor()
        print(given_deck_token)
        select_query = """SELECT COUNT(*) FROM questions where deck_token =(%s) """
        cursor.execute(select_query, (given_deck_token,))
        count = cursor.fetchone()
        # remove tuple from count
        count_int = str(count)[1:-2]
    except (Exception, psycopg2.Error) as e:  # as error :
        print(format(e))

    return count_int


def play_deck_message(update, context):
    update.message.reply_text("Enter deck token to play! \n\nTo cancel, type /cancel.")
    context.chat_data["counter"] = 0 # initialize counter

    return PLAY_DECK


def select_questions_and_answer_from_deck(deck_token):
    try:
        connection = database_connection()
        cursor = connection.cursor()
        select_query = """SELECT question, answer FROM questions where deck_token =(%s) """
        cursor.execute(select_query, (deck_token,))
        questions_and_answers = cursor.fetchall()

    except (Exception, psycopg2.Error) as e:  # as error :
        print(format(e))

    return questions_and_answers


def play_deck(update, context):
    deck_token = update.message.text
    context.chat_data["curr_deck_token"] = deck_token
    if deck_token == "/cancel":
        cancel(update, context)
        return CHOOSING
    else:
        if int(check_if_token_is_valid(deck_token)) == int(0):
            update.message.reply_text("This deck token is either invalid or the deck is empty. Please try again. "
                                      " \n\nTo cancel, type /cancel.")
        else:
            questions_and_answer = select_questions_and_answer_from_deck(deck_token)
            context.chat_data["questions_and_ans"] = select_questions_and_answer_from_deck(deck_token)
            context.chat_data["num_of_qn"] = len(context.chat_data["questions_and_ans"])

            # first question
            context.chat_data["question"] = questions_and_answer[context.chat_data["counter"]][0]
            # first answer
            context.chat_data["answer"] = questions_and_answer[context.chat_data["counter"]][1]

        update.message.reply_text(context.chat_data["question"])

        update.message.reply_text("Please enter your answer.")
        return WAITING_FOR_USER_ANS


def give_user_question(update, context):
    if context.chat_data["counter"] == context.chat_data["num_of_qn"]:
        update.message.reply_text("That was the end of the quiz!")
        return CHOOSING
    else:
        deck_token = context.chat_data["curr_deck_token"]
        questions_and_answer = select_questions_and_answer_from_deck(deck_token)
        context.chat_data["question"] = questions_and_answer[context.chat_data["counter"]][0]
        context.chat_data["answer"] = questions_and_answer[context.chat_data["counter"]][1]
        update.message.reply_text(context.chat_data["question"])
        update.message.reply_text("Please enter your answer.")

    return WAITING_FOR_USER_ANS

# called upon WAITING_FOR_USER_ANS state
def validate_user_answer(update, context):
    user_answer = update.message.text
    if user_answer == "/cancel":
        cancel(update, context)
        return CHOOSING
    if user_answer == context.chat_data["answer"]:
        update.message.reply_text("Good Job! That's the correct answer!! To cancel, type /cancel.")
    else:
        update.message.reply_text("Good Try! But the correct answer is " + context.chat_data["answer"] +
                                  ".  To cancel, type /cancel.")
    # reply_keyboard = [['Yes', 'No']]
    # update.message.reply_text("Proceed to add questions to your new deck?",
    #                           reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    
    context.chat_data["counter"] = context.chat_data["counter"] + 1 # Pull next question and answer
    give_user_question(update, context)
    # return GIVE_USER_QUESTION


def view_all_decks_message(update, context):
    bot_message = "Here are the decks created by you." + "\n\n" + "| Deck Name | Token | \n\n"
    bot_message2 = "Enter a deck token to play! \n\nTo cancel, type /cancel."

    try:
        connection = database_connection()
        cursor = connection.cursor()
        select_query = """SELECT deck_name, deck_token FROM decks """
        cursor.execute(select_query)
        question_set = cursor.fetchall()

        count = 1
        for items in question_set:
            bot_message = bot_message + (str(count) + ". " + items[0] + " | " + items[1]) + "\n\n"
            count = count + 1

        update.message.reply_text(bot_message)
        update.message.reply_text(bot_message2)
    except (Exception, psycopg2.Error) as e:  # as error :
        print(format(e))

    return PLAY_DECK


def view_my_decks_message(update, context):
    bot_message = "Here are the decks created by you." + "\n\n" + "| Deck Name | Token | \n\n"

    try:
        connection = database_connection()
        cursor = connection.cursor()
        select_query = """SELECT deck_name, deck_token FROM decks where deck_owner =(%s) """
        cursor.execute(select_query, (update.message.from_user.username,))
        question_set = cursor.fetchall()

        count = 1
        for items in question_set:
            bot_message = bot_message + (str(count) + ". " + items[0] + " | " + items[1]) + "\n\n"
            count = count + 1

        update.message.reply_text(bot_message)

    except (Exception, psycopg2.Error) as e:  # as error :
        print(format(e))

    return CHOOSING


def motivate(update, context):
    # image
    # f = r"https://dog.ceo/api/breeds/image/random"
    f = r"https://random.dog/woof.json"
    page = requests.get(f)
    data = json.loads(page.text)

    # message
    arr = ["keep up the good work!", "you got this!", "you're doing great!", "you can do it!"]
    rand = random.randint(0, 3)
    file = open("motivational_quotes.txt")
    lines = file.readlines()
    rand_quote = random.randint(0, 17)
    message = lines[rand_quote]

    update.message.reply_text('{}, '.format(update.message.from_user.first_name) + str(arr[rand]))
    update.message.reply_text(message)

    update.message.reply_photo(data["url"])
    return CHOOSING


def cancel(update, context):
    update.message.reply_text("Cancelled!", reply_markup=markup)
    return CHOOSING


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def done(update, context):
    update.message.reply_text("Thanks for playing! Come back soon! To start the bot again, type /start")
    return ConversationHandler.END

def leaderboards(update, context):
    leaderboard = "🏆 Leaderboard 🏆\n\n"
    leaderboard += "1. 🥇 Lim Si Ting\n"
    leaderboard += "2. 🥈 Michaelia Tan Tong\n"
    leaderboard += "3. 🥉 Kimberly Ong\n"
    leaderboard += "4. Yoong Yi En\n"
    leaderboard += "5. John Lee \n"
    leaderboard += "6. Alice Tan \n"
    leaderboard += "7. Peter Tan \n"
    leaderboard += "8. Samantha Wong \n"
    leaderboard += "9. Lin Bei Fong \n"
    leaderboard += "10. Toph Bei Fong \n"
    update.message.reply_text(leaderboard)
    return CHOOSING

def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("help", help))

    # handle button press
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                MessageHandler(Filters.regex('Create Deck'), create_deck_message),
                MessageHandler(Filters.regex('Play Deck'), play_deck_message),
                MessageHandler(Filters.regex('View All Decks'), view_all_decks_message),
                MessageHandler(Filters.regex('View My Decks'), view_my_decks_message),
                MessageHandler(Filters.regex('Leaderboards'), leaderboards),
                MessageHandler(Filters.regex('Motivate Me!'), motivate)

            ],
            CREATE_DECK: [MessageHandler(Filters.text, create_deck)],
            PLAY_DECK: [MessageHandler(Filters.text, play_deck)],
            CREATE_QUESTIONS: [MessageHandler(Filters.text, create_questions)],
            CREATE_ANSWERS: [MessageHandler(Filters.text, create_answers)],
            WAITING_FOR_USER_ANS: [MessageHandler(Filters.text, validate_user_answer)]
        },
        fallbacks=[CommandHandler('done', done)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)
    # updater.start_polling()

    updater.start_webhook(listen="0.0.0.0",
                         port=int(PORT),
                        url_path=TOKEN)
    updater.bot.setWebhook('https://lifehackbots.herokuapp.com/' + TOKEN)

    updater.idle()


if __name__ == '__main__':
    main()
