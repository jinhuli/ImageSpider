'''
本文件实现了一些公共使用的工具
'''
import numpy as np
import cv2 as cv

def _calculate(image1, image2): 
    '''
    Description: 计算单个通道的相似度
    '''
    hist1 = cv.calcHist([image1],[0],None,[256],[0.0,255.0]) 
    hist2 = cv.calcHist([image2],[0],None,[256],[0.0,255.0]) 
    # 计算直方图的重合度 
    degree = 0 
    for i in range(len(hist1)): 
        if hist1[i] != hist2[i]: 
            degree = degree + (1 - abs(hist1[i]-hist2[i])/max(hist1[i],hist2[i])) 
        else: 
            degree = degree + 1 
    degree = degree/len(hist1) 
    return degree

def compute_similarity_by_rgb_hist(img1_path, img2_path):
    '''
    Description: 通过RGB直方图计算两张图片的相似度
    Args:
        img1_path: 图片1路径
        img2_path: 图片2路径
    Return:
        返回相似度值
    '''
    # 将图像resize后，分离为三个通道，再计算每个通道的相似值
    img1 = cv.imread(img1_path)
    img2 = cv.imread(img2_path)
    if img1 is None or img2 is None:
        return 0
    sub_image1 = cv.split(img1) 
    sub_image2 = cv.split(img2) 
    sub_data = 0 
    for im1,im2 in zip(sub_image1,sub_image2): 
        sub_data += _calculate(im1,im2) 
    sub_data = sub_data/3 
    return sub_data
