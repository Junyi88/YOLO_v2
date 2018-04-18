# -*- coding:utf-8 -*-
#
# Written by leeyoshinari
#
# 2018-04-18

import os
import cv2
import numpy as np
import yolo.config as cfg
import xml.etree.ElementTree as ET

class Pascal_voc(object):
    def __init__(self):
        self.pascal_voc = os.path.join(cfg.DATA_DIR, 'Pascal_voc')
        self.image_size = cfg.IMAGE_SIZE
        self.batch_size = cfg.BATCH_SIZE
        self.cell_size = cfg.CELL_SIZE
        self.classes = cfg.CLASSES
        self.num_classes = len(self.classes)
        self.box_per_cell = cfg.BOX_PRE_CELL
        self.class_to_ind = dict(zip(self.classes, range(self.num_classes)))

        self.count = 0
        self.epoch = 1
        self.count_t = 0

    def load_labels(self, model):
        if model == 'train':
            self.devkil_path = os.path.join(self.pascal_voc, 'VOCdevkit')  # 文件路径
            self.data_path = os.path.join(self.devkil_path, 'VOC2007')
            txtname = os.path.join(self.data_path, 'ImageSets', 'Main', 'trainval.txt')
        if model == 'test':
            self.devkil_path = os.path.join(self.pascal_voc, 'VOCdevkit-test')  # 文件路径
            self.data_path = os.path.join(self.devkil_path, 'VOC2007')
            txtname = os.path.join(self.data_path, 'ImageSets', 'Main', 'test.txt')

        with open(txtname, 'r') as f:
            image_ind = [x.strip() for x in f.readlines()]

        labels = []
        for ind in image_ind:
            label, num = self.load_data(ind)
            if num == 0:
                continue
            imagename = os.path.join(self.data_path, 'JPEGImages', ind + '.jpg')
            labels.append({'imagename': imagename, 'labels': label})
        np.random.shuffle(labels)
        return labels


    def load_data(self, index):
        imagename = os.path.join(self.data_path, 'JPEGImages', index + '.jpg')
        image = cv2.imread(imagename)
        h_ratio = 1.0 * self.image_size / image.shape[0]
        w_ratio = 1.0 * self.image_size / image.shape[1]

        label = np.zeros([self.cell_size, self.cell_size, self.box_per_cell, 5 + self.num_classes])
        filename = os.path.join(self.data_path, 'Annotations', index + '.xml')
        tree = ET.parse(filename)
        objects = tree.findall('object')

        for obj in objects:
            box = obj.find('bndbox')
            x1 = max(min((float(box.find('xmin').text)) * w_ratio, self.image_size), 0)
            y1 = max(min((float(box.find('ymin').text)) * h_ratio, self.image_size), 0)
            x2 = max(min((float(box.find('xmax').text)) * w_ratio, self.image_size), 0)
            y2 = max(min((float(box.find('ymax').text)) * h_ratio, self.image_size), 0)
            class_ind = self.class_to_ind[obj.find('name').text.lower().strip()]
            boxes = [0.5 * (x1 + x2), 0.5 * (y1 + y2), np.sqrt((x2 - x1) / self.image_size), np.sqrt((y2 - y1) / self.image_size)]
            cx = 1.0 * boxes[0] * self.cell_size / self.image_size
            cy = 1.0 * boxes[1] * self.cell_size / self.image_size
            boxes[0] = cx - np.floor(cx)
            boxes[1] = cy - np.floor(cy)
            #boxes += [int(np.floor(cy) * self.cell_size + np.floor(cx))]
            xind = int(np.floor(cx))
            yind = int(np.floor(cy))
            #if label[boxes[4],: , 0] == 1:
            #    continue
            label[yind, xind, :, 0] = [1] * self.box_per_cell
            label[yind, xind, :, 1:5] = [boxes[:4]] * self.box_per_cell
            label[yind, xind, :, 5 + class_ind] = 1

        return label, len(objects)


    def next_batches(self, label):
        images = np.zeros([self.batch_size, self.image_size, self.image_size, 3])
        labels = np.zeros([self.batch_size, self.cell_size, self.cell_size, self.box_per_cell, 5 + self.num_classes])
        num = 0
        while num < self.batch_size:
            imagename = label[self.count]['imagename']
            images[num, :, :, :] = self.image_read(imagename)
            labels[num, :, :, :, :] = label[self.count]['labels']
            num += 1
            self.count += 1
            if self.count >= len(label):
                np.random.shuffle(label)
                self.count = 0
                self.epoch += 1
        return images, labels


    def next_batches_test(self, label):
        imagename = []
        images = np.zeros([self.batch_size, self.image_size, self.image_size, 3])
        labels = np.zeros([self.batch_size, self.cell_size, self.cell_size, self.box_per_cell, 5 + self.num_classes])
        num = 0
        while num < self.batch_size:
            imagename.append(label[self.count_t]['imagename'])
            images[num, :, :, :] = self.image_read(imagename[num])
            labels[num, :, :, :, :] = label[self.count_t]['labels']
            num += 1
            self.count_t += 1
            if self.count_t >= len(label):
                self.count_t = 0
        return imagename, images, labels


    def image_read(self, imagename):
        image = cv2.imread(imagename)
        image = cv2.resize(image, (self.image_size, self.image_size))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
        image = image / 255.0 * 2.0 - 1.0
        return image