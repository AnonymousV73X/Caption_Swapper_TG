import telebot
import json

# Replace 'YOUR_BOT_TOKEN' with your actual Telegram bot token
TOKEN = '6709721228:AAGCzFOhtmxr7vlYoBH02gX7ixdw-6RvAAQ'
bot = telebot.TeleBot(TOKEN)

# Define states
WRITE_MODE, READ_MODE = range(2)

# Initial state is read mode
bot_user_states = {}

# A list to store data temporarily
temp_data = []



# Load the true_data.json file
with open('true_data.json', 'r') as file:
    true_data = json.load(file)

def save_data(new_data):
    global true_data  # Declare that we are using the global variable

    try:
        # Read existing data from true_data.json
        with open('true_data.json', 'r') as file:
            existing_data = json.load(file)

        # Append new data to existing data
        existing_data.extend(new_data)

        # Write combined data back to true_data.json
        with open('true_data.json', 'w') as file:
            json.dump(existing_data, file, indent=4)

        # Update the global variable with the latest data
        true_data = existing_data

    except FileNotFoundError:
        # If true_data.json doesn't exist, create it and write new_data
        with open('true_data.json', 'w') as file:
            json.dump(new_data, file, indent=4)

        # Update the global variable with the latest data
        true_data = new_data


@bot.message_handler(commands=['write'])
def enter_write_mode(message):
    # Set user state to write mode
    bot_user_states[message.from_user.id] = WRITE_MODE
    bot.reply_to(message, "You are now in write mode. Send documents to add to true_data.json. Type /save to save all data.")

@bot.message_handler(commands=['read'])
def enter_read_mode(message):
    # Set user state to read mode
    bot_user_states[message.from_user.id] = READ_MODE
    bot.reply_to(message, "You are now in read mode. Send /unread to exit read mode.")

@bot.message_handler(commands=['unread'])
def exit_read_mode(message):
    # Set user state to default (read mode)
    bot_user_states[message.from_user.id] = READ_MODE
    bot.reply_to(message, "Exited read mode.")

@bot.message_handler(commands=['save'])
def save_command(message):
    # Save all data to true_data.json
    save_data(temp_data)

    # Respond to the user
    bot.reply_to(message, "Data saved to true_data.json!")

    # Clear temporary data
    temp_data.clear()

import re

# Function to clean and extract keywords from file names
def clean_file_name(file_name):
    # Use the first 30 characters
    cleaned_name = file_name[:60]

    # Remove special characters, leaving only alphanumeric and spaces
    cleaned_name = re.sub(r'[^a-zA-Z0-9\s]', '', cleaned_name)

    return cleaned_name


# Function to clean the caption
def clean_caption(caption):
    # Remove everything after '@' in the caption
    caption = re.sub(r'@.*', '', caption, flags=re.DOTALL)

    return caption.strip()



@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        user_id = message.from_user.id

        # Get user state
        user_state = bot_user_states.get(user_id, READ_MODE)

        if user_state == WRITE_MODE:
            # Extract information
            file_name = message.document.file_name
            file_caption = clean_caption(message.caption) if message.caption else f"{file_name}"
            file_size = message.document.file_size

            # Clean the file name
            cleaned_file_name = clean_file_name(file_name)

            # Add data to the temporary list
            temp_data.append({
                cleaned_file_name: [
                    [
                        f"{round(file_size / (1024 * 1024), 2)} MB",
                        file_caption
                    ]
                ]
            })

            # Respond to the user
            bot.reply_to(message, f"File {cleaned_file_name} information added. Type /save to save all data!")

        elif user_state == READ_MODE:
            # Get the document details from Telegram metadata
            file_id = message.document.file_id
            file_name = message.document.file_name

            # Clean the file name
            cleaned_file_name = clean_file_name(file_name)

            # Check if the cleaned file name matches any entry in true_data.json
            for entry in true_data:
                entry_file_name = list(entry.keys())[0]  # Extract the file name from the entry

                if cleaned_file_name == clean_file_name(entry_file_name):
                    # Get the information for the matched file name
                    info_list = entry[entry_file_name][0]
                    file_size, alt_file_name = info_list

                    # Send the document back to the user with the information
                    caption = f"{alt_file_name}"
                    bot.send_document(message.chat.id, file_id, caption=caption)
                    return

            bot.send_message(message.chat.id, f"{cleaned_file_name}File name not found in true_data.json.")

    except Exception as e:
        bot.send_message(message.chat.id, f"An error occurred: {str(e)}")
        
        
        
        
        
        
# Dictionary to store user states (merge mode or not)
user_states = {}   
        
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Use /merge to start merge mode.")

@bot.message_handler(commands=['merge'])
def start_merge_mode(message):
    # Set user state to merge mode
    user_states[message.chat.id] = {'merge_mode': True, 'collected_messages': []}

    # Check for additional text in the command
    command_parts = message.text.split(' ', 1)
    if len(command_parts) > 1:
        additional_text = command_parts[1]
        user_states[message.chat.id]['additional_text'] = additional_text
        bot.reply_to(message, f"You are now in merge mode with additional text: {additional_text}. Send your text messages. Type /done when finished.")
    else:
        bot.reply_to(message, "You are now in merge mode. Send your text messages. Type /done when finished.")

@bot.message_handler(commands=['done'])
@bot.message_handler(commands=['done'])
def end_merge_mode(message):
    chat_id = message.chat.id
    user_state = user_states.get(chat_id)

    if user_state and user_state.get('merge_mode'):
        # Extract links from collected messages
        links = extract_links(user_state['collected_messages'])

        if links:
            # Use additional text if available, otherwise omit it
            additional_text = user_state.get('additional_text', '')
            merged_message = '\n'.join([f"{link} -m {additional_text} -z" if additional_text else f"{link}" for link in links])

            # Send the merged message back to the user
            bot.reply_to(message, f"\n{merged_message}")

            # Reset user state
            del user_states[chat_id]
        else:
            bot.reply_to(message, "No links found. Please add links in your messages.")
    else:
        bot.reply_to(message, "You are not in merge mode. Use /merge to start.")


def extract_links(messages):
    # Regular expression to extract the first link from each message
    link_pattern = r'https?://[^\s]+'
    links = []

    for message in messages:
        # Find the first link in the message using the pattern
        match = re.search(link_pattern, message)
        if match:
            links.append(match.group())

    return links

@bot.message_handler(func=lambda message: True)
def handle_text_message(message):
    chat_id = message.chat.id
    user_state = user_states.get(chat_id)

    if user_state and user_state.get('merge_mode'):
        # Collect text messages while in merge mode
        user_state['collected_messages'].append(message.text)
    else:
        bot.reply_to(message, "You are not in merge mode. Use /merge to start.")

# Add a command handler to set additional text
@bot.message_handler(commands=['settext'])
def set_additional_text(message):
    chat_id = message.chat.id
    user_state = user_states.get(chat_id)

    if user_state and user_state.get('merge_mode'):
        # Extract additional text from the command
        command_parts = message.text.split(' ', 1)
        if len(command_parts) > 1:
            additional_text = command_parts[1]
            user_states[chat_id]['additional_text'] = additional_text
            bot.reply_to(message, f"Additional text set to: {additional_text}")
        else:
            bot.reply_to(message, "Please provide additional text after the command.")
    else:
        bot.reply_to(message, "You are not in merge mode. Use /merge to start.")
# Start the bot
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        # Log the exception, or handle it as needed
        print(f"Error: {e}")
