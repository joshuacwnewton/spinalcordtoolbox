#!/usr/bin/env python
#########################################################################################
#
# Visualizer for MRI volumes
#
#
# ---------------------------------------------------------------------------------------
# Copyright (c) 2015 Polytechnique Montreal <www.neuro.polymtl.ca>
# Authors: Benjamin De Leener
# Created: 2015-01-30
# Modified: 2016-02-26
#
# About the license: see the file LICENSE.TXT
#########################################################################################
import sys
from msct_parser import Parser
from msct_image import Image
from bisect import bisect
from numpy import arange, max, pad, linspace, mean, median, std, percentile
import numpy as np
from msct_types import *
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


# from matplotlib.widgets import Slider, Button, RadioButtons


class SinglePlot:
    """
        This class manages mouse events on one image.
    """
    def __init__(self, ax, images, viewer, view=2, display_cross=True):
        self.axes = ax
        self.images = images  # this is a list of images
        self.viewer = viewer
        self.view = view
        self.display_cross = display_cross

        self.image_dim = self.images[0].data.shape
        self.figs = []

        data_to_display = None
        self.cross_to_display = None
        self.aspect_ratio = None
        if self.view == 1:
            self.cross_to_display = [[[self.viewer.current_point.y, self.viewer.current_point.y], [0, self.image_dim[1]]],
                                     [[0, self.image_dim[2]], [self.viewer.current_point.z, self.viewer.current_point.z]]]
            self.aspect_ratio = self.viewer.aspect_ratio[0]
            for image in images:
                data_to_display = image.data[int(self.image_dim[0] / 2), :, :]
                self.figs.append(self.axes.imshow(data_to_display, aspect=self.aspect_ratio))
                self.figs[-1].set_cmap('gray')
                self.figs[-1].set_interpolation('nearest')
        elif self.view == 2:
            self.cross_to_display = [[[self.viewer.current_point.x, self.viewer.current_point.x], [0, self.image_dim[2]]],
                                     [[0, self.image_dim[0]], [self.viewer.current_point.z, self.viewer.current_point.z]]]
            self.aspect_ratio = self.viewer.aspect_ratio[1]
            for image in images:
                data_to_display = image.data[:, int(self.image_dim[1] / 2), :]
                self.figs.append(self.axes.imshow(data_to_display, aspect=self.aspect_ratio))
                self.figs[-1].set_cmap('gray')
                self.figs[-1].set_interpolation('nearest')
        elif self.view == 3:
            self.cross_to_display = [[[self.viewer.current_point.x, self.viewer.current_point.x], [0, self.image_dim[1]]],
                                     [[0, self.image_dim[0]], [self.viewer.current_point.y, self.viewer.current_point.y]]]
            self.aspect_ratio = self.viewer.aspect_ratio[2]
            for image in images:
                data_to_display = image.data[:, :, int(self.image_dim[2] / 2)]
                self.figs.append(self.axes.imshow(data_to_display, aspect=self.aspect_ratio))
                self.figs[-1].set_cmap('gray')
                self.figs[-1].set_interpolation('nearest')

        self.axes.set_axis_bgcolor('black')
        self.axes.set_xticklabels([])
        self.axes.set_yticklabels([])

        if display_cross:
            self.line_vertical = Line2D(self.cross_to_display[0][1], self.cross_to_display[0][0], color='white')
            self.line_horizontal = Line2D(self.cross_to_display[1][1], self.cross_to_display[1][0], color='white')
            self.axes.add_line(self.line_vertical)
            self.axes.add_line(self.line_horizontal)

        self.zoom_factor = 1.0

    def connect(self):
        """
        connect to all the events we need
        :return:
        """
        self.cidpress_click = self.figs[0].figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidscroll = self.figs[0].figure.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.cidrelease = self.figs[0].figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion = self.figs[0].figure.canvas.mpl_connect('motion_notify_event', self.on_motion)

    def draw(self):
        self.figs[0].figure.canvas.draw()

    def update_slice(self, target, data_update=True):
        """
        This function change the viewer to update the current slice
        :param target: number of the slice to go on
        :param data_update: False if you don't want to update data
        :return:
        """
        data = None
        if isinstance(target, list):
            target_slice = target[self.view - 1]
            list_remaining_views = list([0, 1, 2])
            list_remaining_views.remove(self.view - 1)
            self.cross_to_display[0][0] = [target[list_remaining_views[0]], target[list_remaining_views[0]]]
            self.cross_to_display[1][1] = [target[list_remaining_views[1]], target[list_remaining_views[1]]]
        else:
            target_slice = target

        if self.view == 1:
            if 0 <= target_slice < self.images[0].data.shape[0]:
                if data_update:
                    for i, image in enumerate(self.images):
                        self.figs[i].set_data(image.data[target_slice, :, :])
                if self.display_cross:
                    self.line_vertical.set_ydata(self.cross_to_display[0][0])
                    self.line_horizontal.set_xdata(self.cross_to_display[1][1])
        elif self.view == 2:
            if 0 <= target_slice < self.images[0].data.shape[1]:
                if data_update:
                    for i, image in enumerate(self.images):
                        self.figs[i].set_data(image.data[:, target_slice, :])
                if self.display_cross:
                    self.line_vertical.set_ydata(self.cross_to_display[0][0])
                    self.line_horizontal.set_xdata(self.cross_to_display[1][1])
        elif self.view == 3:
            if 0 <= target_slice < self.images[0].data.shape[2]:
                if data_update:
                    for i, image in enumerate(self.images):
                        self.figs[i].set_data(image.data[:, :, target_slice])
                if self.display_cross:
                    self.line_vertical.set_ydata(self.cross_to_display[0][0])
                    self.line_horizontal.set_xdata(self.cross_to_display[1][1])

        self.figs[0].figure.canvas.draw()

    def on_press(self, event):
        """
        when pressing on the screen, add point into a list, then change current slice
        if finished, close the window and send the result
        :param event:
        :return:
        """
        if event.button == 1 and event.inaxes == self.axes:
            self.viewer.on_press(event, self)

        elif event.button == 3 and event.inaxes == self.axes:
            self.viewer.change_intensity(event, self)

        return

    def change_intensity(self, min_intensity, max_intensity):
        self.figs[0].set_clim(min_intensity, max_intensity)
        self.figs[0].figure.canvas.draw()

    def on_motion(self, event):
        if event.button == 1 and event.inaxes == self.axes:
            return self.viewer.on_motion(event, self)

        elif event.button == 3 and event.inaxes == self.axes:
            return self.viewer.change_intensity(event, self)

        else:
            return

    def on_release(self, event):
        if event.button == 1 and event.inaxes == self.axes:
            return self.viewer.on_release(event, self)

        elif event.button == 3 and event.inaxes == self.axes:
            return self.viewer.change_intensity(event, self)

        else:
            return

    def update_xy_lim(self, x_center=None, y_center=None, x_scale_factor=1.0, y_scale_factor=1.0, zoom=True):
        # get the current x and y limits
        cur_xlim = self.axes.get_xlim()
        cur_ylim = self.axes.get_ylim()

        if x_center is None:
            x_center = (cur_xlim[1] - cur_xlim[0]) / 2.0
        if y_center is None:
            y_center = (cur_ylim[1] - cur_ylim[0]) / 2.0

        # Get distance from the cursor to the edge of the figure frame
        x_left = x_center - cur_xlim[0]
        x_right = cur_xlim[1] - x_center
        y_top = y_center - cur_ylim[0]
        y_bottom = cur_ylim[1] - y_center

        if zoom:
            scale_factor = (x_scale_factor + y_scale_factor) / 2.0
            if 0.005 < self.zoom_factor * scale_factor <= 3.0:
                self.zoom_factor *= scale_factor

                self.axes.set_xlim([x_center - x_left * x_scale_factor, x_center + x_right * x_scale_factor])
                self.axes.set_ylim([y_center - y_top * y_scale_factor, y_center + y_bottom * y_scale_factor])
                self.figs[0].figure.canvas.draw()
        else:
            self.axes.set_xlim([x_center - x_left * x_scale_factor, x_center + x_right * x_scale_factor])
            self.axes.set_ylim([y_center - y_top * y_scale_factor, y_center + y_bottom * y_scale_factor])
            self.figs[0].figure.canvas.draw()

    def on_scroll(self, event):
        """
        when scrooling with the wheel, image is zoomed toward position on the screen
        :param event:
        :return:
        """
        if event.inaxes == self.axes:
            base_scale = 0.5
            xdata, ydata = event.xdata, event.ydata

            if event.button == 'up':
                # deal with zoom in
                scale_factor = 1 / base_scale
            elif event.button == 'down':
                # deal with zoom out
                scale_factor = base_scale
            else:
                # deal with something that should never happen
                scale_factor = 1.0
                print event.button

            self.update_xy_lim(x_center=xdata, y_center=ydata,
                               x_scale_factor=scale_factor, y_scale_factor=scale_factor,
                               zoom=True)

        return


class Viewer(object):
    def __init__(self, list_images):
        self.images = []
        for im in list_images:
            if isinstance(im, Image):
                self.images.append(im)
            else:
                print "Error, one of the images is actually not an image..."

            # TODO: check same space
            # TODO: check if at least one image

        # initialisation of plot
        self.fig = plt.figure(figsize=(8, 8))
        self.fig.subplots_adjust(bottom=0.1, left=0.1)
        self.fig.patch.set_facecolor('lightgrey')

        # pad the image so that it is square in axial view (useful for zooming)
        self.image_dim = self.images[0].data.shape
        nx, ny, nz, nt, px, py, pz, pt = self.images[0].dim
        self.im_spacing = [px, py, pz]
        self.aspect_ratio = [float(self.im_spacing[1]) / float(self.im_spacing[2]),
                             float(self.im_spacing[0]) / float(self.im_spacing[2]),
                             float(self.im_spacing[0]) / float(self.im_spacing[1])]
        self.offset = [0.0, 0.0, 0.0]
        self.current_point = Coordinate([int(nx / 2), int(ny / 2), int(nz / 2)])

        self.windows = []
        self.press = [0, 0]

    def compute_offset(self):
        max_size = max([self.image_dim[0], self.image_dim[1], self.image_dim[2]])
        self.offset = [int(round((max_size - self.image_dim[0]) * self.aspect_ratio[0] / 2.0)),
                       int(round((max_size - self.image_dim[1]) * self.aspect_ratio[1] / 2.0)),
                       int(round((max_size - self.image_dim[2]) * self.aspect_ratio[2] / 2.0))]

    def pad_data(self):
        for image in self.images:
            image.data = pad(image.data,
                             ((self.offset[0], self.offset[0]),
                              (self.offset[1], self.offset[1]),
                              (self.offset[2], self.offset[2])),
                             'constant',
                             constant_values=(0, 0))

    def setup_intensity(self):
        # TODO: change for segmentation images
        for i, image in enumerate(self.images):
            flattened_volume = image.flatten()
            self.first_percentile = percentile(flattened_volume[flattened_volume > 0], 0)
            self.last_percentile = percentile(flattened_volume[flattened_volume > 0], 99)
            self.mean_intensity = percentile(flattened_volume[flattened_volume > 0], 98)
            self.std_intensity = self.last_percentile - self.first_percentile
            min_intensity = self.mean_intensity - self.std_intensity
            max_intensity = self.mean_intensity + self.std_intensity

            for window in self.windows:
                window.figs[i].set_clim(min_intensity, max_intensity)

    def is_point_in_image(self, target_point):
        return 0 <= target_point.x < self.image_dim[0] and 0 <= target_point.y < self.image_dim[1] and 0 <= target_point.z < self.image_dim[2]

    def change_intensity(self, event, plot=None):
        if event.xdata and abs(event.xdata - self.press[0]) < 1 and abs(event.ydata - self.press[1]) < 1:
            self.press = event.xdata, event.ydata
            return

        xlim, ylim = plot.axes.get_xlim(), plot.axes.get_ylim()
        mean_intensity_factor = (event.xdata - xlim[0]) / float(xlim[1] - xlim[0])
        std_intensity_factor = (event.ydata - ylim[1]) / float(ylim[0] - ylim[1])
        mean_factor = self.mean_intensity - (mean_intensity_factor - 0.5) * self.mean_intensity * 3.0
        std_factor = self.std_intensity + (std_intensity_factor - 0.5) * self.std_intensity * 2.0
        min_intensity = mean_factor - std_factor
        max_intensity = mean_factor + std_factor

        for window in self.windows:
            window.change_intensity(min_intensity, max_intensity)

    def draw(self):
        for window in self.windows:
            window.fig.figure.canvas.draw()

    def start(self):
        plt.show()


class ThreeViewer(Viewer):
    """
    This class is a visualizer for volumes (3D images) and ask user to click on axial slices.
    Assumes AIL orientation
    """
    def __init__(self, list_images):
        super(ThreeViewer, self).__init__(list_images)

        self.compute_offset()
        self.pad_data()

        self.current_point = Coordinate([int(self.images[0].data.shape[0] / 2),
                                         int(self.images[0].data.shape[1] / 2),
                                         int(self.images[0].data.shape[2] / 2)])

        ax = self.fig.add_subplot(221)
        self.windows.append(SinglePlot(ax=ax, images=self.images, viewer=self, view=2))

        ax = self.fig.add_subplot(222)
        self.windows.append(SinglePlot(ax=ax, images=self.images, viewer=self, view=1))

        ax = self.fig.add_subplot(223)
        self.windows.append(SinglePlot(ax=ax, images=self.images, viewer=self, view=3))

        for window in self.windows:
            window.connect()

        self.setup_intensity()

    def get_event_coordinates(self, event, plot=None):
        point = None
        if plot.view == 1:
            point = Coordinate([self.current_point.x,
                                int(event.ydata),
                                int(event.xdata), 1])
        elif plot.view == 2:
            point = Coordinate([int(event.ydata),
                                self.current_point.y,
                                int(event.xdata), 1])
        elif plot.view == 3:
            point = Coordinate([int(event.ydata),
                                int(event.xdata),
                                self.current_point.z, 1])
        return point

    def move(self, event, plot):
        if event.xdata and abs(event.xdata - self.press[0]) < 1 and abs(event.ydata - self.press[1]) < 1:
            self.press = event.xdata, event.ydata
            return

        self.current_point = self.get_event_coordinates(event, plot)
        point = [self.current_point.x, self.current_point.y, self.current_point.z]
        for window in self.windows:
            if window is plot:
                window.update_slice(point, data_update=False)
            else:
                window.update_slice(point, data_update=True)

        self.press = event.xdata, event.ydata
        return

    def on_press(self, event, plot=None):
        if event.button == 1:
            return self.move(event, plot)
        else:
            return

    def on_motion(self, event, plot=None):
        if event.button == 1:
            return self.move(event, plot)
        else:
            return

    def on_release(self, event, plot=None):
        if event.button == 1:
            return self.move(event, plot)
        else:
            return


class ClickViewer(Viewer):
    """
    This class is a visualizer for volumes (3D images) and ask user to click on axial slices.
    Assumes AIL orientation
    """
    def __init__(self, list_images):
        super(ClickViewer, self).__init__(list_images)

        self.current_slice = 0
        self.number_of_slices = 0
        self.gap_inter_slice = 0

        self.compute_offset()
        self.pad_data()

        # display axes, specific to viewer
        ax = self.fig.add_subplot(111, axisbg='k')
        self.windows.append(SinglePlot(ax, self.images, self, view=2, display_cross=False))
        self.windows[0].connect()

        # specialized for Click viewer
        self.list_points = []
        self.list_points_useful_notation = ''

        # compute slices to display
        self.list_slices = []
        if self.number_of_slices != 0 and self.gap_inter_slice != 0:  # mode multiple points with fixed gap
            central_slice = int(self.image_dim[1] / 2)
            first_slice = central_slice - (self.number_of_slices / 2) * self.gap_inter_slice
            last_slice = central_slice + (self.number_of_slices / 2) * self.gap_inter_slice
            if first_slice < 0:
                first_slice = 0
            if last_slice >= self.image_dim[1]:
                last_slice = self.image_dim[1] - 1
            self.list_slices = [int(item) for item in
                                linspace(first_slice, last_slice, self.number_of_slices, endpoint=True)]
        elif self.number_of_slices != 0:
            self.list_slices = [int(item) for item in
                                linspace(0, self.image_dim[1] - 1, self.number_of_slices, endpoint=True)]
            if self.list_slices[-1] != self.image_dim[1] - 1:
                self.list_slices.append(self.image_dim[1] - 1)
        elif self.gap_inter_slice != 0:
            self.list_slices = list(arange(0, self.image_dim[1], self.gap_inter_slice))
            if self.list_slices[-1] != self.image_dim[1] - 1:
                self.list_slices.append(self.image_dim[1] - 1)
        else:
            self.gap_inter_slice = int(max([round(self.image_dim[1] / 15.0), 1]))
            self.number_of_slices = int(round(self.image_dim[1] / self.gap_inter_slice))
            self.list_slices = [int(item) for item in
                                linspace(0, self.image_dim[1] - 1, self.number_of_slices, endpoint=True)]
            if self.list_slices[-1] != self.image_dim[1] - 1:
                self.list_slices.append(self.image_dim[1] - 1)

        self.windows[0].fig.set_data(self.image.data[:, int(self.list_slices[self.current_slice]), :])
        plt.title('Please select a new point on slice ' + str(self.list_slices[self.current_slice]) + '/' + str(
            self.image_dim[1] - 1) + ' (' + str(self.current_slice + 1) + '/' + str(len(self.list_slices)) + ')')

        # variable to check if all slices have been processed
        self.all_processed = False

        self.setup_intensity()

    def compute_offset(self):
        max_size = max([self.image_dim[0], self.image_dim[2]])
        self.offset = [int(round((max_size - self.image_dim[0]) * self.aspect_ratio[0] / 2.0)),
                       0,
                       int(round((max_size - self.image_dim[2]) * self.aspect_ratio[2] / 2.0))]

    def on_press(self, event, plot=None):
        target_point = Coordinate([int(event.ydata) - self.offset[0], int(self.list_slices[self.current_slice]), int(event.xdata) - self.offset[2], 1])
        if self.is_point_in_image(target_point):
            self.list_points.append(target_point)

            self.current_slice += 1
            if self.current_slice < len(self.list_slices):
                self.windows[0].update_slice(self.list_slices[self.current_slice])
                title_obj = plt.title('Please select a new point on slice ' +
                                      str(self.list_slices[self.current_slice]) + '/' +
                                      str(self.image_dim[1] - 1) + ' (' +
                                      str(self.current_slice + 1) + '/' +
                                      str(len(self.list_slices)) + ')')
                plt.setp(title_obj, color='k')
                self.draw()
            else:
                for coord in self.list_points:
                    if self.list_points_useful_notation != '':
                        self.list_points_useful_notation += ':'
                    self.list_points_useful_notation = self.list_points_useful_notation + str(coord.x) + ',' + str(
                        coord.y) + ',' + str(coord.z) + ',' + str(coord.value)
                self.all_processed = True
                plt.close()
        else:
            title_obj = plt.title('The point you selected in not in the image. Please try again.')
            plt.setp(title_obj, color='r')
            self.draw()

    def on_release(self, event, plot=None):
        return

    def on_motion(self, event, plot=None):
        return

    def get_results(self):
        if self.list_points:
            return self.list_points
        else:
            return None

    def start(self):
        super(ClickViewer, self).start()

        if self.all_processed:
            return self.list_points_useful_notation
        else:
            return None


def get_parser():
    parser = Parser(__file__)
    parser.usage.set_description('Volume Viewer')
    parser.add_option(name="-i",
                      type_value=[[','], 'file'],
                      description="Images to display.",
                      mandatory=True,
                      example="anat.nii.gz")

    parser.add_option(name='-mode',
                      type_value='multiple_choice',
                      description="Display mode ",
                      mandatory=False,
                      default_value='viewer',
                      example=['viewer', 'axial'])

    parser.add_option(name="-v",
                      type_value="multiple_choice",
                      description="""Verbose. 0: nothing. 1: basic. 2: extended.""",
                      mandatory=False,
                      default_value='0',
                      example=['0', '1', '2'])

    return parser

#=======================================================================================================================
# Start program
#=======================================================================================================================
if __name__ == "__main__":
    parser = get_parser()

    arguments = parser.parse(sys.argv[1:])

    list_images = [Image(arg) for arg in arguments["-i"]]

    mode = arguments['-mode']
    if mode == 'viewer':
        viewer = ThreeViewer(list_images)
        viewer.start()
    elif mode == 'axial':
        viewer = ClickViewer(list_images)
        viewer.start()
