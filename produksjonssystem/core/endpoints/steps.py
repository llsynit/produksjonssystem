import os

from flask import jsonify, request

import core.server

from core.endpoints.directories import getDirectoryEditions, getDirectoryEdition
from core.pipeline import Pipeline
from core.directory import Directory
from core.utils.metadata import Metadata
from core.utils.filesystem import Filesystem



@core.server.route(core.server.root_path + '/steps/', require_auth=None)
def steps():
    core.server.expected_args(request, [])

    return getSteps()


@core.server.route(core.server.root_path + '/pipelines/', require_auth=None)
def deprecated_pipelines():
    return steps()


def getSteps():
    result = {}
    for pipeline in Pipeline.pipelines:
        result[pipeline.uid] = pipeline.title
    return jsonify(result), 200


@core.server.route(core.server.root_path + '/steps/<step_id>/', require_auth=None)
def step(step_id):
    core.server.expected_args(request, [])

    return getStep(step_id)


@core.server.route(core.server.root_path + '/pipelines/<step_id>/', require_auth=None)
def deprecated_pipeline(step_id):
    return step(step_id)


def getStep(step_id):
    pipeline = [pipeline for pipeline in Pipeline.pipelines if pipeline.uid == step_id]
    pipeline = pipeline[0] if pipeline else None

    if not pipeline:
        return None, 404

    dir_in_id = None
    dir_out_id = None
    for dir in Directory.dirs_flat:
        if pipeline.dir_in and os.path.normpath(pipeline.dir_in) == os.path.normpath(Directory.dirs_flat[dir]):
            dir_in_id = dir
        if pipeline.dir_out and os.path.normpath(pipeline.dir_out) == os.path.normpath(Directory.dirs_flat[dir]):
            dir_out_id = dir

    return jsonify({
        "uid": pipeline.uid,
        "title": pipeline.title,
        "dir_in": dir_in_id,
        "dir_out": dir_out_id,
        "parentdirs": pipeline.parentdirs,
        "labels": pipeline.labels,
        "publication_format": pipeline.publication_format,
        "expected_processing_time": pipeline.expected_processing_time,
        "state": pipeline.get_state(),
        "queue": pipeline.get_queue()
    }), 200


@core.server.route(core.server.root_path + '/steps/<step_id>/creative-works/', require_auth=None)
def step_creativeWorks(step_id):
    core.server.expected_args(request, [])

    return "TODO", 501


@core.server.route(core.server.root_path + '/pipelines/<step_id>/creative-works/', require_auth=None)
def deprecated_pipeline_creativeWorks(step_id, creative_work):
    return step_creativeWorks(step_id)


@core.server.route(core.server.root_path + '/steps/<step_id>/creative-works/<creative_work_id>/', require_auth=None)
def step_creativeWork(step_id, creative_work_id):
    core.server.expected_args(request, [])

    return "TODO", 501


@core.server.route(core.server.root_path + '/steps/<step_id>/editions/', require_auth=None)
def step_editions(step_id):
    core.server.expected_args(request, [])

    return getStepEditions(step_id)


@core.server.route(core.server.root_path + '/pipelines/<step_id>/editions/', require_auth=None)
def deprecated_pipelines_editions(step_id):
    return step_editions(step_id)


def getStepEditions(step_id):
    pipeline = [pipeline for pipeline in Pipeline.pipelines if pipeline.uid == step_id]
    pipeline = pipeline[0] if pipeline else None

    if not pipeline:
        return None, 404

    else:
        directory_id = [dir for dir in Directory.dirs_flat if os.path.normpath(Directory.dirs_flat[dir]) == os.path.normpath(pipeline.dir_out)][:1]
        directory_id = directory_id[0] if directory_id else None
        return getDirectoryEditions(directory_id)


@core.server.route(core.server.root_path + '/steps/<step_id>/editions/<edition_id>', require_auth=None)
def step_edition(step_id, edition_id):
    core.server.expected_args(request, [])

    return getStepEdition(step_id, edition_id)


@core.server.route(core.server.root_path + '/pipelines/<step_id>/editions/<edition_id>', require_auth=None)
def deprecated_pipeline_edition(step_id, edition_id):
    return getStepEdition(step_id, edition_id)


def getStepEdition(step_id, edition_id):
    pipeline = [pipeline for pipeline in Pipeline.pipelines if pipeline.uid == step_id]
    pipeline = pipeline[0] if pipeline else None

    if not pipeline:
        return None, 404

    else:
        directory_id = [dir for dir in Directory.dirs_flat if os.path.normpath(Directory.dirs_flat[dir]) == os.path.normpath(pipeline.dir_out)][:1]
        directory_id = directory_id[0] if directory_id else None
        return getDirectoryEdition(directory_id, edition_id, False, "GET")


@core.server.route(core.server.root_path + '/steps/<step_id>/editions/<edition_id>/trigger', require_auth=None, methods=["GET", "PUT", "POST"])
def step_trigger(step_id, edition_id):
    core.server.expected_args(request, [])

    return triggerStepEdition(step_id, edition_id)


@core.server.route(core.server.root_path + '/pipelines/<step_id>/editions/<edition_id>/trigger', require_auth=None, methods=["GET", "PUT", "POST"])
def deprecated_pipeline_trigger(step_id, edition_id):
    return step_trigger(step_id, edition_id)


def triggerStepEdition(step_id, edition_id):
    pipeline = [pipeline for pipeline in Pipeline.pipelines if pipeline.uid == step_id]
    pipeline = pipeline[0] if pipeline else None

    if not pipeline:
        return None, 404

    else:
        pipeline.trigger(edition_id, auto=False)
        return jsonify([step_id]), 200
@core.server.route(core.server.root_path + '/pipelines/progress_report/', require_auth=None)
def progress_report():
    uids = []
    for pipeline in Pipeline.pipelines:
        print(pipeline)
        print(pipeline.uid)
        uids.append(pipeline.uid)
    progress_report_data = progress_report(uids)
    return jsonify(progress_report_data), 200

def get_book_count(dir, parentdirs=None):
        books = []
        if parentdirs is None:
            print("dir {} parentdirs {}".format(dir, parentdirs))
        else:
            print("no parent dir {}".format(dir))
            for d in dir:
                if os.path.isdir(d):
                    books += Filesystem.list_book_dir(d)
            print(len(books))
        return len(books)
def progress_report(uids):
        """
        This method will generate a progress report with dynamic values
        and return them for use in frontend rendering.
        """

        report_data = []
        for uid in uids:
            pipeline = None
            for p in Pipeline.pipelines:
                if p.uid == uid:
                    pipeline = p
                    break
            if not pipeline:
                continue
            print(pipeline.dir_in)
            group_pipeline = pipeline.get_current_group_pipeline()

            title = group_pipeline.get_group_title()
            pipeline_id = group_pipeline.get_group_id()

            queue = group_pipeline.get_queue()
            queue_created = len([book for book in queue if Pipeline.get_main_event(book) == "created"]) if queue else 0
            queue_deleted = len([book for book in queue if Pipeline.get_main_event(book) == "deleted"]) if queue else 0
            queue_modified = len([book for book in queue if Pipeline.get_main_event(book) == "modified"]) if queue else 0
            queue_triggered = len([book for book in queue if Pipeline.get_main_event(book) == "triggered"]) if queue else 0
            queue_autotriggered = len([book for book in queue if Pipeline.get_main_event(book) == "autotriggered"]) if queue else 0

            queue_string = {
                "created": queue_created,
                "modified": queue_modified,
                "deleted": queue_deleted,
                "triggered": queue_triggered,
                "autotriggered": queue_autotriggered
            }

            queue_size = len(queue) if queue else 0

            book = Metadata.pipeline_book_shortname(group_pipeline)

            # Simplified input and output path handling
            relpath_in = None
            relpath_out = None
            state = group_pipeline.get_state()
            status = group_pipeline.get_status()
            progress_text = group_pipeline.get_progress()

            if pipeline.dir_in:
                relpath_in = os.path.basename(os.path.dirname(pipeline.dir_in))

            if pipeline.dir_out:
                relpath_out = os.path.basename(os.path.dirname(pipeline.dir_out))

            book_count_in = get_book_count(pipeline.dir_in)
            book_count_out = get_book_count(pipeline.dir_out, pipeline.parentdirs)

            pipeline_data = {
                "title": title,
                #"queue_string": queue_string,
                #"queue_size": queue_size,
                "book_count_in": book_count_in,
                "book_count_out": book_count_out,
                #"book": book,
                "relpath_in": relpath_in,
                "relpath_out": relpath_out,
                "state": state,
                "status": status,
                "progress_text": progress_text,

            }
            #print("pipeline_label {} state {} status {} progress_text {} label_out {} book_count_out".format(pipeline_label,state, status, label_out,progress_text, book_count_out))

            report_data.append(pipeline_data)

        return report_data