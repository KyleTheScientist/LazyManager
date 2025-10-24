import xmltodict
import json
import shutil
import subprocess
from pathlib import Path

try:
    MASTER_GAMES = Path(__file__).parent / "resource/MasterGamesDefault.xml"
    GAME_SET = Path("./gameset.xml")
    GAMES_LOCAL = next(Path().cwd().glob("MGP_Release*")) / 'GameCatalog/'
    GAMES_REMOTE = Path("D:/MGP/GameCatalog")
    GAMES_CONFIGURED_XML = Path("E:/Config/GamesConfigured.xml")
    STORAGE = Path("E:/Storage")
except Exception as e:
    MASTER_GAMES = Path(__file__).parent / "resource/MasterGamesDefault.xml"
    GAME_SET = Path("./gameset.xml")
    GAMES_LOCAL = next(Path("G:/").parent.glob("MGP_Release*")) / 'GameCatalog/'
    GAMES_REMOTE = Path("C:/tmp")
    GAMES_CONFIGURED_XML = Path("C:/tmp/GamesConfigured.xml")
    STORAGE = Path("E:/Storage")

def load_games() -> dict:
    if not MASTER_GAMES.exists():
        raise FileNotFoundError(f"MasterGamesDefault.xml not found at {MASTER_GAMES}")

    data = xmltodict.parse(MASTER_GAMES.read_text())
    # with open("MasterGamesDefault.json", "w") as f:
    #     json.dump(data, f, indent=4)
    # dump this to a file
    games = {}
    jurisdiction = [jurisdiction for jurisdiction in data["Games"]["GamingJurisdiction"] if jurisdiction['@Value'] == "ClassII"][0]
    for entry in jurisdiction['Entry']:
        entry['@Theme'] = 0
        entry['@Active'] = "true"

        if '@AllowedPercentages' in entry:
            del entry['@AllowedPercentages']
        key = f"{entry['@GameID']}_{entry['@PaytableName']}"
        games[key] = entry
    return games

def load_gameset_xml() -> dict:
    data = xmltodict.parse(GAME_SET.read_text()[3:]) # skip the BOM
    gameset = {}
    for entry in data["GameSet"]["Title"]:
        gameset[entry["@ThemeID"]] = entry
    return gameset

def load_gameset_txt(master: dict) -> dict:
    lines = Path("gameset.txt").read_text().splitlines()
    gameset = {}
    for line in lines:
        if line.strip() == "" or line.startswith("#"):
            continue
        directory, paytable = line.split(',')
        directory, paytable = directory.strip(), paytable.strip()
        for key, game in master.items():
            if game['@Directory'] == directory and game['@PaytableName'] == paytable:
                id = game['@GameID']
                gameset[id] = {
                    "@ThemeID": id,
                    "@Payout": "94",  # default to 94
                    "@PaytableName": paytable
                }
                break
        else:
            print(f"Warning: No matching game found for Directory={directory}, PaytableName={paytable}")

    return gameset

def generate_games_xml(master: dict, gameset: dict):
    games_dict = {
        "Games": {
            "@GameSetName": "NeoMGPTest1",
            "@GameSetFileName": "F:\\GameSets\\20250919100030GSVertical.xml",
            "@DefaultGameID": "",
            "@GamingJurisdiction": "ClassII",
            "@MaxGameTitles": "9",
            "@GameSetFileSignature": "49285B922A1EFE97461BFBB635BB3D34247C7033",
            "Entry": []
        }
    }
    
    if gameset:
        first_game_id = list(gameset.keys())[0]
        games_dict["Games"]["@DefaultGameID"] = first_game_id
    
    for theme_id, game_info in gameset.items():
        key = f"{theme_id}_{game_info['@PaytableName']}"
        if key not in master:
            print(f"Warning: Key {key} not found in master games, skipping...")
            continue
        
        master_entry = master[key]
        
        entry = {
            "@GameID": master_entry.get("@GameID", ""),
            "@DisplayName": master_entry.get("@DisplayName", ""),
            "@Directory": master_entry.get("@Directory", ""),
            "@PaytableName": master_entry.get("@PaytableName", ""),
            "@Percentage": master_entry.get("@Percentage", ""),
            "@Denoms": master_entry.get("@Denoms", ""),
            "@Progressives": master_entry.get("@Progressives", ""),
            "@Order": master_entry.get("@Order", "0"),
            "@Theme": master_entry.get("@Theme", "0"),
            "@Active": master_entry.get("@Active", "true"),
        }
        
        if "@VariantName" in master_entry:
            entry["@VariantName"] = master_entry["@VariantName"]
        
        games_dict["Games"]["Entry"].append(entry)
    
    xml_output = xmltodict.unparse(games_dict, pretty=True, indent="  ")
    with open(str(GAMES_CONFIGURED_XML.resolve()), "w", encoding='utf-8') as f:
        f.write(xml_output)
    print(f"Generated {GAMES_CONFIGURED_XML} with {len(games_dict['Games']['Entry'])} entries")
    
    return xml_output


def copy_games(master: dict, gameset: dict):
    for game in gameset.values():
        key = f"{game['@ThemeID']}_{game['@PaytableName']}"
        directory = master[key]["@Directory"]
        source = GAMES_LOCAL / directory
        dest = GAMES_REMOTE / directory
        if not source.exists():
            print(f"Source directory {source} does not exist, skipping...")
            continue
        if dest.exists():
            print(f"Destination directory {dest} already exists, deleting...")
            shutil.rmtree(dest)

        print(f"Copying {source} to {dest}...")
        subprocess.run(f'xcopy "{source}" "{dest}" /E /I /H /Y', shell=True)

master = load_games()

if not GAME_SET.exists():
    print("Loading gameset.txt")
    gameset = load_gameset_txt(master)
else:
    print("Loading gameset.xml")
    gameset = load_gameset_xml()

print(json.dumps(gameset, indent=4))

generate_games_xml(master, gameset)
copy_games(master, gameset)
shutil.rmtree(STORAGE, ignore_errors=True)


# pyinstaller --noconfirm --onefile --console --add-data "resource/*;resource" --name LazyFDC main.py
