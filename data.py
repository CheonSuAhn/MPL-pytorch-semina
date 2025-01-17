import logging
import math

import numpy as np
from PIL import Image
from torchvision import datasets
from torchvision import transforms

from augmentation import RandAugment

logger = logging.getLogger(__name__)

cifar10_mean = (0.4914, 0.4822, 0.4465)
cifar10_std = (0.2471, 0.2435, 0.2616)
cifar100_mean = (0.5071, 0.4867, 0.4408)
cifar100_std = (0.2675, 0.2565, 0.2761)
normal_mean = (0.5, 0.5, 0.5)
normal_std = (0.5, 0.5, 0.5)

# only comment about cifar10 dataset
def get_cifar10(args):
    # setting transform for labeled data (weak augmentation)
    transform_labeled = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomCrop(size=args.resize,
                              padding=int(args.resize*0.125),
                              padding_mode='reflect'),
        transforms.ToTensor(),
        transforms.Normalize(mean=cifar10_mean, std=cifar10_std)
    ])
    # setting transform for validation(test) data (no augmentation)
    transform_val = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=cifar10_mean, std=cifar10_std)
    ])
    # setting the base dataset to CIFAR10
    base_dataset = datasets.CIFAR10(args.data_path, train=True, download=True)
       
    # setting index to split train datset into labeled and unlabeled dataset
    train_labeled_idxs, train_unlabeled_idxs = x_u_split(args, base_dataset.targets)
    
    # setting train labeled dataset using transform for labeled data
    train_labeled_dataset = CIFAR10SSL(
        args.data_path, train_labeled_idxs, train=True,
        transform=transform_labeled
    )
    
    # setting train unlabeled dataset using TransformMPL(transform for unlabeled data)
    train_unlabeled_dataset = CIFAR10SSL(
        args.data_path, train_unlabeled_idxs,
        train=True,
        transform=TransformMPL(args, mean=cifar10_mean, std=cifar10_std)
    )
    
    # setting test dataset using transform for validation(test) data
    test_dataset = datasets.CIFAR10(args.data_path, train=False,
                                    transform=transform_val, download=False)
    # return the test dataset and training dataset composed of labeled and unlabeled dataset
    return train_labeled_dataset, train_unlabeled_dataset, test_dataset


def get_cifar100(args):

    transform_labeled = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomCrop(size=args.resize,
                              padding=int(args.resize*0.125),
                              padding_mode='reflect'),
        transforms.ToTensor(),
        transforms.Normalize(mean=cifar100_mean, std=cifar100_std)])

    transform_val = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=cifar100_mean, std=cifar100_std)])

    base_dataset = datasets.CIFAR100(args.data_path, train=True, download=True)

    train_labeled_idxs, train_unlabeled_idxs = x_u_split(args, base_dataset.targets)

    train_labeled_dataset = CIFAR100SSL(
        args.data_path, train_labeled_idxs, train=True,
        transform=transform_labeled
    )

    train_unlabeled_dataset = CIFAR100SSL(
        args.data_path, train_unlabeled_idxs, train=True,
        transform=TransformMPL(args, mean=cifar100_mean, std=cifar100_std)
    )

    test_dataset = datasets.CIFAR100(args.data_path, train=False,
                                     transform=transform_val, download=False)

    return train_labeled_dataset, train_unlabeled_dataset, test_dataset

# split train datset into labeled and unlabeled dataset according to the pre-defined labeled data number(args.num_labeled)
def x_u_split(args, labels):
    label_per_class = args.num_labeled // args.num_classes
    labels = np.array(labels)
    labeled_idx = []
    # unlabeled data: all training data
    unlabeled_idx = np.array(range(len(labels)))
    for i in range(args.num_classes):
        idx = np.where(labels == i)[0]
        idx = np.random.choice(idx, label_per_class, False)
        labeled_idx.extend(idx)
    labeled_idx = np.array(labeled_idx)
    assert len(labeled_idx) == args.num_labeled

    if args.expand_labels or args.num_labeled < args.batch_size:
        num_expand_x = math.ceil(
            args.batch_size * args.eval_step / args.num_labeled)
        labeled_idx = np.hstack([labeled_idx for _ in range(num_expand_x)])
    np.random.shuffle(labeled_idx)
    return labeled_idx, unlabeled_idx
    # number of labeled dataset is pre-defined and number of unlabeled datset is same as all training dataset


def x_u_split_test(args, labels):
    label_per_class = args.num_labeled // args.num_classes
    labels = np.array(labels)
    labeled_idx = []
    unlabeled_idx = []
    for i in range(args.num_classes):
        idx = np.where(labels == i)[0]
        np.random.shuffle(idx)
        labeled_idx.extend(idx[:label_per_class])
        unlabeled_idx.extend(idx[label_per_class:])
    labeled_idx = np.array(labeled_idx)
    unlabeled_idx = np.array(unlabeled_idx)
    assert len(labeled_idx) == args.num_labeled

    if args.expand_labels or args.num_labeled < args.batch_size:
        num_expand_x = math.ceil(
            args.batch_size * args.eval_step / args.num_labeled)
        labeled_idx = np.hstack([labeled_idx for _ in range(num_expand_x)])

    np.random.shuffle(labeled_idx)
    np.random.shuffle(unlabeled_idx)
    return labeled_idx, unlabeled_idx

# transform for unlabeled data
class TransformMPL(object):
    def __init__(self, args, mean, std):
        # setting the hyperparameter for random augmentation
        if args.randaug:
            n, m = args.randaug
        else:
            n, m = 2, 10  # default
        
        # original data transformed with weak augmentation
        self.ori = transforms.Compose([
            transforms.RandomHorizontalFlip(),
            transforms.RandomCrop(size=args.resize,
                                  padding=int(args.resize*0.125),
                                  padding_mode='reflect')])
        # augmented data transformed with strong augmentation (random augmentation)
        self.aug = transforms.Compose([
            transforms.RandomHorizontalFlip(),
            transforms.RandomCrop(size=args.resize,
                                  padding=int(args.resize*0.125),
                                  padding_mode='reflect'),
            RandAugment(n=n, m=m)])
        
        # normalization according to the dataset
        self.normalize = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std)])

    def __call__(self, x):
        ori = self.ori(x)
        aug = self.aug(x)   # transform using strong augmentation (random augmentation)
        return self.normalize(ori), self.normalize(aug) # output two data(batchsize * 2) (weak augmentation and strong augmentation)


class CIFAR10SSL(datasets.CIFAR10):
    def __init__(self, root, indexs, train=True,
                 transform=None, target_transform=None,
                 download=False):
        super().__init__(root, train=train,
                         transform=transform,
                         target_transform=target_transform,
                         download=download)
        if indexs is not None:
            self.data = self.data[indexs]
            self.targets = np.array(self.targets)[indexs]

    def __getitem__(self, index):
        img, target = self.data[index], self.targets[index]
        img = Image.fromarray(img)

        if self.transform is not None:
            img = self.transform(img)

        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target


class CIFAR100SSL(datasets.CIFAR100):
    def __init__(self, root, indexs, train=True,
                 transform=None, target_transform=None,
                 download=False):
        super().__init__(root, train=train,
                         transform=transform,
                         target_transform=target_transform,
                         download=download)
        if indexs is not None:
            self.data = self.data[indexs]
            self.targets = np.array(self.targets)[indexs]

    def __getitem__(self, index):
        img, target = self.data[index], self.targets[index]
        img = Image.fromarray(img)

        if self.transform is not None:
            img = self.transform(img)

        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target


DATASET_GETTERS = {'cifar10': get_cifar10,
                   'cifar100': get_cifar100}
