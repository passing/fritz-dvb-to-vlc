#!/usr/bin/python3

import argparse
import re
import requests
import xml.etree.ElementTree as ET

categories = {
    "TV HD": {
        "m3u_path": "dvb/m3u/tvhd.m3u",
        "logo_url": "https://tv.avm.de/tvapp/logos/hd",
    },
    "TV SD": {
        "m3u_path": "dvb/m3u/tvsd.m3u",
        "logo_url": "https://tv.avm.de/tvapp/logos",
    },
    "Radio": {
        "m3u_path": "dvb/m3u/radio.m3u",
        "logo_url": "https://tv.avm.de/tvapp/logos/radio",
    },
}

logo_replace = [
    ("ä", "ae"),
    ("ö", "oe"),
    ("ü", "ue"),
    ("ß", "ss"),
    ("[ /]+", "_"),
    ("[.,-]", ""),
]


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        type=str,
        default="dvb",
        metavar="HOSTNAME",
        help="hostname of FRITZ!WLAN Repeater DVB-C",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dvb.xspf",
        metavar="FILENAME",
        help="output filename",
    )
    return parser.parse_args()


def get_m3u_channels(m3u_url):
    channels = {}

    # download m3u playlist
    result = requests.get(m3u_url)

    # split m3u playlist
    lines = result.text.split("\n")

    for l in range(1, len(lines) - 1, 3):
        # title from 1st line
        title = re.sub("^#EXTINF:0,", "", lines[l]).strip()
        # option from 2nd line
        option = re.sub("^#EXTVLCOPT:", "", lines[l + 1])
        # url from 3rd line
        url = lines[l + 2]

        channels[title] = {"option": option, "url": url}

    return channels


def get_channel_image(title, logo_url):
    image = title.lower()

    # replace patterns in image name
    for pattern, repl in logo_replace:
        image = re.sub(pattern, repl, image)

    logo_url = "{}/{}.png".format(logo_url, image)

    return logo_url


def add_playlist_logos(channels, url):
    for title, channel in channels.items():
        channel["image"] = get_channel_image(title, url)


def export_xspf_playlist(channel_lists, filename):
    # create playlist root element
    playlist = ET.Element("playlist")
    playlist.set("xmlns", "http://xspf.org/ns/0/")
    playlist.set("xmlns:vlc", "http://www.videolan.org/vlc/playlist/ns/0/")
    playlist.set("version", "1")

    # create playlist title, tracklist and playlist tree
    ET.SubElement(playlist, "title").text = "DVB"
    tracklist = ET.SubElement(playlist, "trackList")
    playlist_tree = ET.SubElement(
        playlist, "extension", application="http://www.videolan.org/vlc/playlist/0"
    )

    # use unique track ID so the playlist can reference the elements in the tracklist
    track_id = 0

    for category, channels in channel_lists.items():
        # create node in playlist tree
        playlist_node = ET.SubElement(playlist_tree, "vlc:node", title=category)

        for title, channel in sorted(channels.items(), key=lambda x: x[0].lower()):
            # add track to tracklist
            track = ET.SubElement(tracklist, "track")
            ET.SubElement(track, "title").text = title
            ET.SubElement(track, "location").text = channel["url"]
            ET.SubElement(track, "image").text = channel["image"]

            # add track extension
            track_ext = ET.SubElement(
                track, "extension", application="http://www.videolan.org/vlc/playlist/0"
            )
            ET.SubElement(track_ext, "vlc:id").text = str(track_id)
            ET.SubElement(track_ext, "vlc:option").text = channel["option"]

            # add track to playlist tree
            ET.SubElement(playlist_node, "vlc:item", tid=str(track_id))

            track_id += 1

    # write xspf playlist to file
    tree = ET.ElementTree(playlist)
    tree.write(filename, encoding="UTF-8", xml_declaration=True)


def main():
    # get arguments
    args = get_arguments()

    # download and convert m3u playlists
    channel_lists = {}
    for category, options in categories.items():
        channels = get_m3u_channels(
            "http://{}/{}".format(args.host, options["m3u_path"])
        )
        add_playlist_logos(channels, options["logo_url"])
        channel_lists[category] = channels

    # export xspf playlist
    export_xspf_playlist(channel_lists, args.output)


if __name__ == "__main__":
    main()
