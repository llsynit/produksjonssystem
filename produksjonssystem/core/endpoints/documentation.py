import os
from flask import jsonify, request, Response
import json
from lxml import etree

import core.server
from core.config import Config

JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../release_notes/release_notes.json")
system_shouldRun_False_Since = None


def load_json_file():
    if not os.path.exists(JSON_FILE):
        return []
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
        return data.get("updates", [])


def dict_to_xml(tag, d):
    elem = etree.Element(tag)
    if isinstance(d, dict):
        for k, v in d.items():
            child = dict_to_xml(k, v)
            elem.append(child)
    elif isinstance(d, list):
        for item in d:
            tag_name = tag[:-1] if tag.endswith('s') else "item"
            child = dict_to_xml(tag_name, item)
            elem.append(child)
    else:
        elem.text = str(d)
    return elem


def xmlify(obj, root_tag):
    xml_obj = dict_to_xml(root_tag, obj)
    xml_str = etree.tostring(xml_obj, pretty_print=True, encoding='utf-8', xml_declaration=True)
    return Response(xml_str, mimetype='application/xml')


def should_return_xml():
    return request.args.get('format') == 'xml' or 'application/xml' in request.headers.get('Accept', '')

@core.server.route(core.server.root_path + '/version/', require_auth=None)
def version():
    updates = load_json_file()

    if not updates:
        if should_return_xml():
            return xmlify({"message": "No updates available"}, "error")
        return jsonify({"message": "No updates available"})

    if should_return_xml():
        return xmlify(updates[0], "version")
    return jsonify(updates[0])

@core.server.route(core.server.root_path + '/version-history/', require_auth=None)
def version_history():
    updates = load_json_file()
    if should_return_xml():
        return xmlify(updates, "versions")
    return jsonify(updates)

    