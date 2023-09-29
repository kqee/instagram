from ast import arg
from instagrapi import Client
from instagrapi.types import Media
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed

from termcolor import colored
from os.path import abspath, isdir, exists, dirname
from os import mkdir
from dotenv import load_dotenv
from os import getenv
from traceback import format_exc
from sys import argv

from instagrapi.exceptions import UserNotFound, PleaseWaitFewMinutes, BadPassword
from pydantic import ValidationError
from requests.exceptions import RetryError
from colorama import just_fix_windows_console

# TODO: add path checking, if not exist, create [DONE]
# NOTE:
# this program doesnt work at times, i am not willing to fix it lolz


just_fix_windows_console() # as stated in the doc, we need this for colorama to work
cwd = dirname(abspath(argv[0]))
load_dotenv(f"{cwd}/.env") # load our vars in .env
USERNAME = getenv('INSTA_USERNAME')
PASSWORD = getenv('INSTA_PASSWORD')
SETTINGS_FILE = f"{cwd}/dumps.json"

def main() -> None:
    args = ArgumentParser()
    group = args.add_mutually_exclusive_group(required=True)
    group.add_argument('--username')
    group.add_argument('--hashtag')
    args.add_argument("--directory", default=".")
    args.add_argument("--limit", default=10, type=int)
    parsed = args.parse_args()
    client = Client()
    # LOGIN AREA
    if USERNAME and PASSWORD:
        print(colored('[-]username and password has been provided, proceeding...', 'blue'))
        try:
            if not exists(SETTINGS_FILE):
                client.login(USERNAME, PASSWORD)
                client.dump_settings(SETTINGS_FILE)
            else: # if this fails, instagram probably banned you
                client.load_settings(SETTINGS_FILE)
                client.login(USERNAME, PASSWORD)
        except BadPassword as e:
            return print(colored(f"[!]encountered an error: {e}", "red"))
        except PleaseWaitFewMinutes:
            return print(colored("[!]you've got to wait for a few minutes, we cannot log in!", "red", "red"))
        print(colored("[-]login successful!", 'blue'))
    else:
        print(colored("[-]both of the input or one of the input is not provided in .env file, proceeding, an error might occur.", 'red'))
                    
    if not isdir(parsed.directory):
            print(colored(f"[!]directory {parsed.directory} does not exist", 'blue'))
            print(colored(f"[-]creating directory {parsed.directory}...", 'blue'))
            mkdir(abspath(parsed.directory))
            
    if parsed.username:
        try:
            userid = get_user_id(client, parsed.username)
        except Exception:
            return

    if parsed.hashtag:
        try:
            hashtags = get_hashtag(client, parsed.hashtag, parsed.limit) # when limit is too high, it stops working
        except Exception:
            return
        
    print(colored("fetching medias...", 'blue'))
    if parsed.username:
        data = client.user_medias(userid, parsed.limit)
    if parsed.hashtag:
        data = hashtags
    with ThreadPoolExecutor() as tpe:
        total = len(data)
        print(colored(f"[-]attempting to download {total} medias", 'blue'))
        futures = {
            tpe.submit(
                check_media_type,
                client,
                url,
                abspath(parsed.directory),
            ): url
            for url in data # enumerate to keep track, somewhat a hack
        }
        
        # below code checks for error, might improve this later on
        for num,future in enumerate(as_completed(futures), start=1):
            url = f"https://instagram/p/{futures[future].code}"
            try:
                print(colored(f"[{num}/{total}]attempting to install {url}", "blue"))
                future.result()
            except Exception as e:
                print(colored(f"[!]failed installing {url} with error: {e}", "red"))
            else:
                print(colored(f"[-]success installing {url} in {abspath(parsed.directory)}", "green"))
    print(colored("done", 'light_green'))

    # non multithreaded way
    # for _,i in enumerate(data, start=1): 
    #     check_media_type(client, i, parsed.directory, str(client.media_info(i).media_type), _, len(data))


def check_media_type(client: Client, data_img: Media, path) -> None:
    download = {
        "1": {
            "download": client.photo_download,
            "type": "photo"
        },
        "2": {
            "download": client.video_download,
            "type": "video"
        },
        "8": {
            "download": client.album_download,
            "type": "album"
        }
    }
    link = f"\"https://instagram.com/p/{data_img.code}\""
    
    path = download[str(data_img.media_type)]['download'](data_img.id, path)
    return path

# write everything twice!!!

def get_user_id(client: Client, username):
    try:
        print(colored('[-]fetching user id...', 'blue'))
        return client.user_id_from_username(username)
    except UserNotFound as e:
        # not needed because instagrapi already notifies the user if the specified user does not exist
        # print(colored(f"cant find user: {username}", e)) 
        raise e
    except RetryError as e:
        print(colored('[!]rate limited! try again later or change your IP!', 'red'))
        raise e
    except Exception as e:
        print(colored("[!]an error occured! check traceback below...", "red"))
        print(colored(format_exc()))
        raise e

def get_hashtag(client: Client, hashtag, limit):
    try:
        print(colored("[-]getting hashtag...", 'blue'))
        return client.hashtag_medias_top_v1(hashtag, limit)
    except ValidationError as e:
        print(colored("[!]it is probable that the hashtag you are looking for does not exist...", "red", "red", "red"))
        raise e
    except PleaseWaitFewMinutes as e:
        print(colored("[!]an error was raised:", e))
        print(colored("[!]you probably are not logged in...", "red", "red", "red"))
        raise e
    except Exception as e:
        print(colored("[!]an error occured! check traceback below...", "red", "red", "red"))
        print(colored(format_exc()))
        raise e

if __name__ == "__main__":
    main()
