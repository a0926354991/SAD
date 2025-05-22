from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os, re, json, time, requests

# ✅ 多個 Google Maps URL（可自行擴充）
url_list = [
    "https://www.google.com/maps/place/%E3%80%8E%E8%8B%A5%E7%99%BD%E6%8B%89%E9%BA%B5%E3%80%8F%E6%BD%AE%E4%B8%89%E6%96%87/@25.0242569,121.5441969,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442ab49e381d407:0x31ef18da0363d370!8m2!3d25.0242572!4d121.5532091!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFfCggvbS8wNDJjawoIL20vMDlnbXMQASoSIg7ml6Ug5byPIOaLiem6tShFMh8QASIbbHhJ_iKDQMPOYrWpTfZ3O65K76f6a1gyvIqEMhIQAiIO5pelIOW8jyDmi4npurXgAQA!16s%2Fg%2F11x6qnndl4?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E4%B8%80%E7%9C%9F%E4%BA%AD%E3%83%A9%E3%83%BC%E3%83%A1%E3%83%B3/@25.0292343,121.5577367,16z/data=!4m7!3m6!1s0x3442ab6c810fcfd1:0x4c2b9bbbee8889f6!8m2!3d25.0287079!4d121.5645754!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11hymgh27v?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/SOMM%C3%89+Ramen+%E6%B3%95%E5%BC%8F%E6%BE%84%E6%B8%85%E7%B3%BB%E6%8B%89%E9%BA%B5/@25.0307168,121.5475121,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442ab24afa10fbb:0x9b626295b054bab5!8m2!3d25.0307163!4d121.5565246!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSAQpyZXN0YXVyYW50mgEjQ2haRFNVaE5NRzluUzBWSlEwRm5UVU4zYlRRMlkyVlJFQUWqAVUKCC9tLzA5Z21zEAEqEiIO5pelIOW8jyDmi4npurUoRTIfEAEiG2x4Sf4ig0DDzmK1qU32dzuuSu-n-mtYMryKhDISEAIiDuaXpSDlvI8g5ouJ6bq14AEA-gEECDQQFw!16s%2Fg%2F11wjqhw7y_?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E4%B9%9D%E6%B9%AF%E5%B1%8B%E6%97%A5%E6%9C%AC%E6%8B%89%E9%BA%B5%E5%8F%B0%E5%8C%97%E5%A4%A7%E5%AE%89%E5%BA%97/@25.0307168,121.5475121,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442abcc834e479d:0xc671d4a9cc18e4ec!8m2!3d25.0308633!4d121.5537911!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11c6s6lshp?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E9%9B%9E%E4%BA%8C%E6%8B%89%E9%BA%B5/@25.032802,121.5406899,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442abcd98b153e9:0x72fba6fab63a247e!8m2!3d25.0328019!4d121.5497023!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11c5559pkh?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E5%8D%81%E4%B8%89%E5%B7%9D%E6%97%A5%E6%9C%AC%E6%8B%89%E9%BA%B5%E5%AE%9A%E9%A3%9F+%E5%A4%A7%E5%AE%89%E5%BA%97/@25.0328867,121.5343723,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442ab643f4d67e5:0x75d0d027aec89c53!8m2!3d25.0328867!4d121.5433845!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARNqYXBhbmVzZV9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11sr_wxzm1?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E6%A3%AE%E6%9C%AC%E5%AE%B6%E6%8B%89%E9%BA%B5/@25.0407768,121.5226704,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a97c73611667:0x586b1ea2ead75ebb!8m2!3d25.0407768!4d121.5316826!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50mgEjQ2haRFNVaE5NRzluUzBWSlEwRm5TVVJDWjE5dVlsSkJFQUWqAVUKCC9tLzA5Z21zEAEqEiIO5pelIOW8jyDmi4npurUoRTIfEAEiG2x4Sf4ig0DDzmK1qU32dzuuSu-n-mtYMryKhDISEAIiDuaXpSDlvI8g5ouJ6bq14AEA-gEECAAQHA!16s%2Fg%2F11cmytsz1y?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E5%B1%AF%E4%BA%AC%E6%8B%89%E9%BA%B5+%E5%8F%B0%E5%8C%97%E7%AB%99%E5%89%8D%E5%BA%97/@25.046103,121.507225,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a972fa9db3b9:0xe3d62764fb57f45c!8m2!3d25.046103!4d121.5162372!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50mgEjQ2haRFNVaE5NRzluUzBWSlEwRm5TVVIxZEc5NllVSjNFQUWqAVUKCC9tLzA5Z21zEAEqEiIO5pelIOW8jyDmi4npurUoRTIfEAEiG2x4Sf4ig0DDzmK1qU32dzuuSu-n-mtYMryKhDISEAIiDuaXpSDlvI8g5ouJ6bq14AEA-gEECAAQGw!16s%2Fg%2F11b6394gbx?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E5%A1%A9%E7%90%89/@25.046103,121.507225,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a9c54e2a997b:0xce274ce69131b5b8!8m2!3d25.0419372!4d121.5130037!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11p0w0h4rv?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E5%8B%9D%E5%8D%81%E8%98%AD+%E5%8D%97%E9%99%BD%E5%BA%97/@25.046103,121.507225,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a9731065e0f3:0xc525fae210c48181!8m2!3d25.0448403!4d121.5161561!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11gfnjlmbg?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E5%A4%AA%E9%99%BD%E8%95%83%E8%8C%84%E6%8B%89%E9%BA%B5+%E7%AB%99%E5%89%8D%E6%9C%AC%E5%BA%97/@25.046103,121.507225,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a972f0683c1f:0xc1dfb96e5171f405!8m2!3d25.0462341!4d121.5164145!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F12hpbgbxw?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E4%B8%80%E9%A2%A8%E5%A0%82%E5%BE%AE%E9%A2%A8%E5%8F%B0%E5%8C%97%E8%BB%8A%E7%AB%99%E5%BA%97/@25.046103,121.507225,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a9727dbb21b9:0xdc63b0757a177184!8m2!3d25.047749!4d121.517044!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F1pzrmkynx?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E3%82%89%E3%81%82%E3%82%81%E3%82%93%E8%8A%B1%E6%9C%88%E5%B5%90+%E5%8F%B0%E5%8C%97%E5%87%B1%E6%92%92%E5%BA%97/@25.046103,121.507225,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a972faf45165:0x5eaecb2146e7a213!8m2!3d25.0460643!4d121.5164947!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50mgEkQ2hkRFNVaE5NRzluUzBWSlEwRm5TVVJETTNOaVZIcEJSUkFCqgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAPoBBQikBRAa!16s%2Fg%2F11f6mf071v?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E8%8C%B6%E6%82%9F%E6%8B%89%E9%BA%B5/@25.0487385,121.511796,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a90016bfbbdb:0xec53a54132c56e49!8m2!3d25.0487385!4d121.5208082!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11y5slnn85?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E9%AC%BC%E9%87%91%E6%A3%92+%E4%B8%AD%E5%B1%B1%E5%88%A5%E9%A4%A8/@25.0487385,121.511796,16z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a984c9dab027:0xa2c54424c7bf3e82!8m2!3d25.0488716!4d121.5208697!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50mgEjQ2haRFNVaE5NRzluUzBWSlEwRm5TVU4wY25OZmNXUm5FQUWqAVUKCC9tLzA5Z21zEAEqEiIO5pelIOW8jyDmi4npurUoRTIfEAEiG2x4Sf4ig0DDzmK1qU32dzuuSu-n-mtYMryKhDISEAIiDuaXpSDlvI8g5ouJ6bq14AEA-gEECC4QJA!16s%2Fg%2F11tmfz5drl?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E4%BA%8C%E5%B1%8B%E7%89%A1%E8%A0%A3%E6%8B%89%E9%BA%B5/@25.0545472,121.5079096,15z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a95893afd45f:0xbedd7a92320eab89!8m2!3d25.0545869!4d121.5202174!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50mgEkQ2hkRFNVaE5NRzluUzBWSlEwRm5TVU5LYUZsbE56WjNSUkFCqgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAPoBBAgAECM!16s%2Fg%2F11t0r2mqxm?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E9%B3%A5%E4%BA%BA%E6%8B%89%E9%BA%B5+%E4%B8%AD%E5%B1%B1%E5%BA%97/@25.0545472,121.5079096,15z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a96f20822da5:0xb1831c40cd4e5fe0!8m2!3d25.0509626!4d121.5229033!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50mgEjQ2haRFNVaE5NRzluUzBWSlEwRm5TVU5sZWpkbGRGbFJFQUWqAVUKCC9tLzA5Z21zEAEqEiIO5pelIOW8jyDmi4npurUoRTIfEAEiG2x4Sf4ig0DDzmK1qU32dzuuSu-n-mtYMryKhDISEAIiDuaXpSDlvI8g5ouJ6bq14AEA-gEFCJkBEBE!16s%2Fg%2F11fy4dhgww?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E6%B1%A0%E9%9F%B3+%E9%B6%8F%E7%99%BD%E6%B9%AF%E3%83%A9%E3%83%BC%E3%83%A1%E3%83%B3/@25.0545472,121.5079096,15z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a95e355d7fa7:0x7426381a1b95b9ab!8m2!3d25.0538213!4d121.5202146!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11rzdg3fk1?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E5%89%B5%E4%BD%9C%E6%8B%89%E9%BA%B5+%E6%82%A0%E7%84%B6/@25.0545472,121.5079096,15z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a95ca3cae895:0xa328ee76f7f41ada!8m2!3d25.0612889!4d121.5269011!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50qgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAA!16s%2Fg%2F11fyly8_sf?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E6%A9%AB%E6%BF%B1%E5%AE%B6%E7%B3%BB%E6%8B%89%E9%BA%B5+%E7%89%B9%E6%BF%83%E5%B1%8B/@25.0545472,121.5079096,15z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a942af7fb877:0xae0ae19b93b3b8cb!8m2!3d25.0573244!4d121.5250309!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50mgEkQ2hkRFNVaE5NRzluUzBWSlEwRm5TVU54YlRWUGVUZFJSUkFCqgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAPoBBAgAECM!16s%2Fg%2F11b7fwcpdw?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/%E9%87%91%E6%B2%A2%E6%8B%89%E9%BA%B5/@25.0596789,121.5128448,15z/data=!4m11!1m3!2m2!1z5pel5byP5ouJ6bq1!6e5!3m6!1s0x3442a9dba82ad7e7:0xcb15d355dde48722!8m2!3d25.0648353!4d121.5253195!15sCgzml6XlvI_mi4npurVaECIO5pelIOW8jyDmi4npurWSARByYW1lbl9yZXN0YXVyYW50mgEkQ2hkRFNVaE5NRzluUzBWSlEwRm5TVVJhYURSRGF6RjNSUkFCqgFVCggvbS8wOWdtcxABKhIiDuaXpSDlvI8g5ouJ6bq1KEUyHxABIhtseEn-IoNAw85italN9nc7rkrvp_prWDK8ioQyEhACIg7ml6Ug5byPIOaLiem6teABAPoBBAgyECE!16s%2Fg%2F11h27zy2xd?entry=ttu&g_ep=EgoyMDI1MDUxNS4xIKXMDSoASAFQAw%3D%3D"
]

# 資料夾
json_dir = "Web Crawler/ramin/json"
img_dir = "Web Crawler/ramin/images"
os.makedirs(json_dir, exist_ok=True)
os.makedirs(img_dir, exist_ok=True)

def clean_text(text):
    return re.sub(r'[^\x00-\x7F\u4e00-\u9fff0-9\-()（）．:： ]+', '', text).strip()

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "", name)

# 啟動瀏覽器
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

try:
    for url in url_list:
        try:
            driver.get(url)
            time.sleep(5)

            store_info = {}

            # 店名
            try:
                store_info["name"] = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf'))).text
            except:
                store_info["name"] = ""
            
            short_name = sanitize_filename(store_info.get("name", "store")[:5])

            # 地址
            try:
                address = driver.find_element(By.XPATH, '//button[contains(@data-item-id,"address")]//div[contains(text(), "市")]')
                store_info["address"] = address.text.strip()
            except:
                store_info["address"] = ""

            # 電話
            try:
                phone_elem = driver.find_element(By.XPATH, '//button[contains(@data-item-id,"phone")]')
                store_info["phone"] = clean_text(phone_elem.text)
            except:
                store_info["phone"] = ""

            # 營業時間
            try:
                block = driver.find_element(By.XPATH, '//div[contains(@aria-label, "營業時間")]')
                store_info["open_time"] = block.get_attribute("aria-label")
            except:
                store_info["open_time"] = ""

            # 評分
            try:
                score = driver.find_element(By.CLASS_NAME, 'fontDisplayLarge')
                store_info["rating"] = float(score.text.strip())
            except:
                store_info["rating"] = None

            # 關鍵字
            try:
                keyword_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.e2moi')
                keyword_pairs = []
                for btn in keyword_buttons:
                    try:
                        text = btn.find_element(By.CSS_SELECTOR, 'span.uEubGf.fontBodyMedium').text.strip()
                        count = btn.find_element(By.CSS_SELECTOR, 'span.bC3Nkc.fontBodySmall').text.strip()
                        count = int(re.sub(r"[^\d]", "", count))
                        if text != "全部" and not text.startswith("+"):
                            keyword_pairs.append((text, count))
                    except:
                        continue
                top_keywords = sorted(keyword_pairs, key=lambda x: x[1], reverse=True)[:3]
                store_info["keywords"] = [kw[0] for kw in top_keywords]
            except:
                store_info["keywords"] = []

            # 菜單圖片
            try:
                img = driver.find_element(By.CSS_SELECTOR, 'img.DaSXdd')
                img_url = re.sub(r'=w\d+-h\d+-[^&]*', '=w1000-h1000', img.get_attribute("src"))
                img_path = os.path.join(img_dir, f"{short_name}_menu.jpg")
                with open(img_path, 'wb') as f:
                    f.write(requests.get(img_url).content)
                store_info["menu_image"] = img_path
            except:
                store_info["menu_image"] = ""

            # 輸出 JSON
            with open(os.path.join(json_dir, f"{short_name}.json"), 'w', encoding='utf-8') as f:
                json.dump({"store_info": store_info}, f, ensure_ascii=False, indent=2)

            print(f"✅ 成功儲存：{short_name}.json 和圖片")

        except Exception as e:
            print(f"❌ 抓取 {url} 失敗：{e}")

finally:
    driver.quit()
