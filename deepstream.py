#!/usr/bin/env python3

################################################################################
# SPDX-FileCopyrightText: Copyright (c) 2019-2021 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

import argparse
import sys

import configparser

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst

import pyds

# dictionary storing the total counted objects from all frames by different sources
TOTAL_COUNT = {}


def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        sys.stderr.write("Warning: %s: %s\n" % (err, debug))
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write("Error: %s: %s\n" % (err, debug))
        loop.quit()
    return True


def cb_new_demuxpad(demux: Gst.Element, pad: Gst.Pad, element: Gst.Element):
    """
    When a new video pad is added, the demux
    needs to connect to the parser to push
    buffers downstream.
    """
    if pad.name == "video_0":
        if pad.link(element.get_static_pad("sink")) != Gst.PadLinkReturn.OK:
            raise Exception("create new demux pad error")


def osd_sink_pad_buffer_probe(pad, info, u_data):
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            if u_data not in TOTAL_COUNT:
                TOTAL_COUNT[u_data] = 0
            l_obj = frame_meta.obj_meta_list
            while l_obj:
                TOTAL_COUNT[u_data] += 1
                l_obj = l_obj.next

            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK


def _create_Gst_element(type: str, name: str) -> Gst.Element:
    element = Gst.ElementFactory.make(type, name)
    print(f"Creating {name}\n")
    if not element:
        sys.stderr.write(f"Unable to create {name} \n")
    return element


def main(args):
    video_path = args.video_path
    disable_tracker = args.disable_tracker

    Gst.init(None)

    # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements
    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

    sources = []
    qtdemuxes = []
    parsers = []
    decoders = []
    queues = []
    nvvidconvs = []
    osds = []
    sinks = []

    for i in range(args.n_sources):
        # sources
        source = _create_Gst_element(type="filesrc", name=f"file-source-{i}")
        qtdemux = _create_Gst_element(type="qtdemux", name=f"qtdemux-{i}")
        parser = _create_Gst_element(type="h264parse", name=f"h264-parser-{i}")
        decoder = _create_Gst_element(type="nvv4l2decoder", name=f"decoder-{i}")

        # sinks
        queue = _create_Gst_element(type="queue", name=f"queue-{i}")
        nvvidconv = _create_Gst_element(
            type="nvvideoconvert", name=f"nvvideoconvert-{i}"
        )
        osd = _create_Gst_element(type="nvdsosd", name=f"osd-{i}")
        sink = _create_Gst_element(type="fakesink", name=f"sink-{i}")

        sources.append(source)
        qtdemuxes.append(qtdemux)
        parsers.append(parser)
        decoders.append(decoder)
        queues.append(queue)
        nvvidconvs.append(nvvidconv)
        osds.append(osd)
        sinks.append(sink)

    # Create nvstreammux instance to form batches from one or more sources.
    streammux = _create_Gst_element(type="nvstreammux", name="nvstreammux")
    pgie = _create_Gst_element(type="nvinfer", name="primary-inference")
    if not disable_tracker:
        tracker = _create_Gst_element(type="nvtracker", name="tracker")
    debatcher = _create_Gst_element(type="nvstreamdemux", name="streamdemux")

    print("Playing file %s " % video_path)
    for source in sources:
        source.set_property("location", video_path)

    streammux.set_property("width", 1920)
    streammux.set_property("height", 1080)
    streammux.set_property("batch-size", args.n_sources)
    streammux.set_property("batched-push-timeout", 4000000)

    # Set properties of pgie and sgie
    pgie.set_property("config-file-path", args.pgie_config)

    # Set properties of tracker
    config = configparser.ConfigParser()
    config.read(args.tracker_config)
    config.sections()

    # Set properties of fakesink
    if args.sync:
        print("Setting sync to true...")
        for sink in sinks:
            sink.set_property("sync", True)

    if not disable_tracker:
        for key in config["tracker"]:
            if key == "tracker-width":
                tracker_width = config.getint("tracker", key)
                tracker.set_property("tracker-width", tracker_width)
            if key == "tracker-height":
                tracker_height = config.getint("tracker", key)
                tracker.set_property("tracker-height", tracker_height)
            if key == "gpu-id":
                tracker_gpu_id = config.getint("tracker", key)
                tracker.set_property("gpu_id", tracker_gpu_id)
            if key == "ll-lib-file":
                tracker_ll_lib_file = config.get("tracker", key)
                tracker.set_property("ll-lib-file", tracker_ll_lib_file)
            if key == "ll-config-file":
                tracker_ll_config_file = config.get("tracker", key)
                tracker.set_property("ll-config-file", tracker_ll_config_file)
            if key == "enable-batch-process":
                tracker_enable_batch_process = config.getint("tracker", key)
                tracker.set_property(
                    "enable_batch_process", tracker_enable_batch_process
                )
            if key == "enable-past-frame":
                tracker_enable_past_frame = config.getint("tracker", key)
                tracker.set_property("enable_past_frame", tracker_enable_past_frame)

    print("Adding elements to Pipeline \n")
    for i in range(args.n_sources):
        pipeline.add(sources[i])
        pipeline.add(qtdemuxes[i])
        pipeline.add(parsers[i])
        pipeline.add(decoders[i])

        pipeline.add(queues[i])
        pipeline.add(nvvidconvs[i])
        pipeline.add(osds[i])
        pipeline.add(sinks[i])

    pipeline.add(streammux)
    pipeline.add(pgie)
    if not disable_tracker:
        pipeline.add(tracker)
    pipeline.add(debatcher)

    print("Linking elements in the Pipeline \n")
    for i in range(args.n_sources):
        # linking sources
        sources[i].link(qtdemuxes[i])
        qtdemuxes[i].connect("pad-added", cb_new_demuxpad, parsers[i])
        parsers[i].link(decoders[i])

        sinkpad = streammux.get_request_pad(f"sink_{i}")
        if not sinkpad:
            sys.stderr.write(" Unable to get the sink pad of streammux \n")
        srcpad = decoders[i].get_static_pad("src")
        if not srcpad:
            sys.stderr.write(" Unable to get source pad of decoder \n")
        srcpad.link(sinkpad)

        # linking sinks
        srcpad = debatcher.get_request_pad(f"src_{i}")
        sinkpad = queues[i].get_static_pad("sink")
        srcpad.link(sinkpad)

        queues[i].link(nvvidconvs[i])
        nvvidconvs[i].link(osds[i])
        osds[i].link(sinks[i])

    # sources -> nvstreammux -> inference -> tracker -> nvstreamdemux -> sinks
    streammux.link(pgie)
    if not disable_tracker:
        pgie.link(tracker)
        tracker.link(debatcher)
    else:
        pgie.link(debatcher)

    # create and event loop and feed gstreamer bus mesages to it
    loop = GLib.MainLoop()

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # Lets add probe to get informed of the meta data generated, we add probe to
    # the sink pad of the osd element, since by that time, the buffer would have
    # had got all the metadata.
    for i in range(args.n_sources):
        osdsinkpad = osds[i].get_static_pad("sink")
        if not osdsinkpad:
            sys.stderr.write(" Unable to get sink pad of nvosd \n")
        osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, i)

    print("Starting pipeline \n")

    # start play back and listed to events
    pipeline.set_state(Gst.State.PLAYING)
    Gst.debug_bin_to_dot_file(pipeline, Gst.DebugGraphDetails.ALL, "debug_graph")

    try:
        loop.run()
    except:
        pass

    # cleanup
    pipeline.set_state(Gst.State.NULL)

    print(f"Total count: {TOTAL_COUNT}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-path", type=str, help="path to video file")
    parser.add_argument(
        "--pgie-config",
        type=str,
        default="./models/pgie/pgie.txt",
        help="path to pgie config",
    )
    parser.add_argument(
        "--tracker-config",
        type=str,
        default="./dstest2_tracker_config.txt",
        help="path to tracker config",
    )
    parser.add_argument(
        "-n",
        "--n_sources",
        type=int,
        default=2,
        help="number of sources going into nvstreamux",
    )
    parser.add_argument(
        "--disable-tracker", action="store_true", help="link tracker in pipeline or not"
    )
    parser.add_argument("--sync", action="store_true", help="sync of fakesink")

    args = parser.parse_args()

    sys.exit(main(args=args))
