import subprocess
import cv2 as cv
import numpy as np
import math
import time

screenshot_command = "adb shell /system/bin/screencap -p /sdcard/Screenshot.png"
pull_command = "adb pull /sdcard/screenshot.png Screenshot/Screenshot.png"
longtouch_format = "adb shell input swipe 500 500 500 500 %d"
restart_command = "adb shell input swipe 580 1580 580 1580 100"
screenshot = None

role_image = cv.cvtColor(cv.imread('Sample/role.png'), cv.COLOR_BGR2HSV)
role_hist = cv.calcHist([role_image], [0, 1], None, [180, 256], [0, 180, 0, 256])
cv.normalize(role_hist, role_hist, 0, 255, cv.NORM_MINMAX)
#cv.namedWindow("Debug")
num_loss = 0

def CheckAdb():
    status, output = subprocess.getstatusoutput("adb version")
    return status == 0

def Repair(bg):     #处理截取背景样本中的非背景色
    det_last = bg[1][0].astype('int16') - bg[0][0].astype('int16')
    for i in range(2, len(bg)):
        det = bg[i][0].astype('int16') - bg[i - 1][0].astype('int16')
        dist = np.sum(det * det) - np.sum(det_last * det_last)      
        if dist > 100:
            return bg[0:i]
    return bg

def GetScreenshot():    #通过adb获取截图
    global screenshot
    print("开始获取截图")
    subprocess.getstatusoutput(screenshot_command)
    subprocess.getstatusoutput(pull_command)
    screenshot = cv.imread("ScreenShot/ScreenShot.png")

def CalRoleAndBoard():  #根据截图找出角色和下一块的坐标
    global screenshot, role_hist
    flag = True
    screenshot = cv.resize(screenshot, (270, 480))
    screenshot = screenshot[100:400, 0:270]
    screenshot_hsv = cv.cvtColor(screenshot, cv.COLOR_BGR2HSV)
    bg = cv.cvtColor(screenshot[0:300, 268:270], cv.COLOR_BGR2HSV)
    bg = Repair(bg)
    bg_hist = cv.calcHist([bg], [0, 1], None, [180, 256], [0, 180, 0, 256])
    cv.normalize(bg_hist, bg_hist, 0, 256, cv.NORM_MINMAX)
    screenshot_temp = cv.calcBackProject([screenshot_hsv], [0, 1], role_hist, [0, 180, 0, 256], 1)
    screenshot_temp = cv.GaussianBlur(screenshot_temp, (5, 5), 5)
    ret, screenshot_temp = cv.threshold(screenshot_temp, 64, 255, cv.THRESH_BINARY) 
    ret, contours, hierarchy = cv.findContours(screenshot_temp, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)  
    x1, y1 = 0, 0
    cnt = 0
    for contour in contours:
        cnt += len(contour)
        for p in contour:
            x1 += p[0][0]
            y1 += p[0][1] 
    if cnt == 0:
        flag = False
    else:
        x1 = int(x1 / cnt)
        y1 = int(y1 / cnt) + 5
    screenshot_temp = cv.calcBackProject([screenshot_hsv], [0, 1], bg_hist, [0, 180, 0, 256], 1)
    screenshot_temp = cv.GaussianBlur(screenshot_temp, (5, 5), 5)
    ret, screenshot_temp = cv.threshold(screenshot_temp, 16, 255, cv.THRESH_BINARY_INV) 
    ret, contours, hierarchy = cv.findContours(screenshot_temp, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    x2, y2 = 9999, 9999
    cnt = 0
    for contour in contours:
        for p in contour:
            if abs(p[0][0] - x1) < 20:
                continue
            if (p[0][1] + 5) < y2:
                cnt = 1
                x2, y2 = p[0][0], p[0][1]
            elif p[0][1] <= y2:
                cnt += 1
                x2, y2 = x2 + p[0][0], y2 + p[0][1]
    x2 = int(x2 / cnt)
    y2 = int(y2 / cnt)
    x0, y0 = x2, int((y1 - y2) * 2 / 5 * abs((((y1 - y2) ** 2) / ((x1 - x2) ** 2)))) + y2
    return flag, x0, y0, x1, y1, x2, y2

def Jump():
    global screenshot, role_hist, num_loss
    GetScreenshot()
    flag, x0, y0 ,x1, y1, x2, y2 = CalRoleAndBoard()
    if not flag:
        num_loss += 1
        print("未检测到角色 %d 次" % num_loss)
        if num_loss >= 3:
            print("重新开始游戏")
            status, output = subprocess.getstatusoutput(restart_command)
    else: num_loss = 0
    cv.line(screenshot, (0, y2), (270, y2), (0, 0, 255))
    cv.line(screenshot, (0, y1), (270, y1), (0, 0, 255))
    cv.line(screenshot, (x2, 0), (x2, 480), (0, 0, 255))
    cv.line(screenshot, (x1, 0), (x1, 480), (0, 0, 255))
    cv.circle(screenshot, (x0, y0), 2, (255, 0, 0), 5)
    cv.circle(screenshot, (x1, y1), 2, (255, 0, 0), 5)
    cv.line(screenshot, (x0, y0), (x1, y1), (255, 0, 0), 3)
    print("起始点(x:%d, y:%d) 目标点(x:%d, y:%d)" % (x1, y1, x0, y0))
    estimated_time = int(math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2) / 0.185)
    if estimated_time < 200: estimated_time = 200
    print("预计触摸时间%dms" % estimated_time)
    status, output = subprocess.getstatusoutput(longtouch_format % estimated_time)

def main():
    global screenshot
    if not CheckAdb():
        print("adb可能未正确配置")
        return
    cv.namedWindow('Screenshot')
    while True:
        Jump()
        print("--------------------------------------")
        cv.imshow('Screenshot', screenshot)
        if cv.waitKey(1500) != -1:
            break
    cv.destroyAllWindows()

if __name__ == '__main__':
    main()