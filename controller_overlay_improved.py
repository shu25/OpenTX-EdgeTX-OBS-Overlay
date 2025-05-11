import pygame
import os
import sys
import math
import threading
import time

# ウィンドウの位置を設定
os.environ['SDL_VIDEO_WINDOW_POS'] = "50,50"
pygame.init()

# クロマキー背景（緑）
CHROMA_COLOR = (0, 255, 0)
WIDTH, HEIGHT = 600, 500  # ウィンドウサイズをさらに拡大
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME | pygame.HWSURFACE)
pygame.display.set_caption("コントローラーオーバーレイ")
clock = pygame.time.Clock()

# ウィンドウを常に最前面に表示する関数
def keep_window_on_top():
    if sys.platform == "win32":
        import ctypes
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            HWND_TOPMOST = -1
            SWP_NOACTIVATE = 0x0010
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            # 最前面に表示しつつ、フォーカスを奪わない設定
            ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 
                                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
            return True
        except Exception as e:
            print(f"Windowsでの最前面表示設定エラー: {e}")
            return False
    elif sys.platform == "darwin":
        # macOSの場合
        print("macOSでは最前面表示の設定が異なる場合があります")
        return False
    else:
        # Linuxの場合
        print("Linuxでは最前面表示の設定が異なる場合があります")
        return False

# 定期的に最前面表示を適用するスレッド
def topmost_thread():
    while True:
        keep_window_on_top()
        time.sleep(1)  # 1秒ごとに確認

# 最前面表示スレッドを開始
topmost_thread = threading.Thread(target=topmost_thread, daemon=True)
topmost_thread.start()

# 初回実行
keep_window_on_top()

# フォント初期化
font = pygame.font.SysFont(None, 24)

# ジョイスティック初期化
joy = None
try:
    pygame.joystick.init()
    joystick_count = pygame.joystick.get_count()
    if joystick_count == 0:
        print("警告: ジョイスティックが見つかりません")
    else:
        joy = pygame.joystick.Joystick(0)
        joy.init()
        print(f"ジョイスティック '{joy.get_name()}' を検出しました")
        print(f"軸の数: {joy.get_numaxes()}")
        print(f"ボタンの数: {joy.get_numbuttons()}")
except Exception as e:
    print(f"初期化エラー: {e}")

# 軸の反転設定
invert = {"lx": False, "ly": True, "rx": False, "ry": True}

# デフォルトの軸マッピング
default_axis_mapping = {
    "lx": 0,      # 左スティック横
    "ly": 1,      # 左スティック縦
    "rx": 3,      # 右スティック横
    "ry": 2       # 右スティック縦（スロットル軸に割り当て）
}

# 現在の軸マッピング
axis_mapping = default_axis_mapping.copy()

# 設定を表示
show_debug = True
show_values = True
show_all_axes = False
config_mode = False
show_ui = True  # UIの表示/非表示を切り替えるフラグ（スティックは常に表示）

# スティックサイズをさらに大きく設定
STICK_SIZE = 180  # スティックのサイズを拡大

def draw_stick(x, y, size, x_val, y_val, invert_x=False, invert_y=True):
    """スティックの位置を点で表示（X軸とY軸を組み合わせて）"""
    # 軸の反転を適用
    x_val = -x_val if invert_x else x_val
    y_val = -y_val if invert_y else y_val
    
    # 十字を描画
    pygame.draw.line(screen, (150, 150, 150), (x - size//2, y), (x + size//2, y), 2)
    pygame.draw.line(screen, (150, 150, 150), (x, y - size//2), (x, y + size//2), 2)
    
    # スティックの位置を白い点で表示
    stick_x = x + int(x_val * size/2)
    stick_y = y + int(y_val * size/2)
    
    # スティックのシャフトを描画
    pygame.draw.line(screen, (200, 200, 200), (x, y), (stick_x, stick_y), 4)
    
    # スティックの先端を描画
    pygame.draw.circle(screen, (255, 255, 255), (stick_x, stick_y), 10)

def draw_throttle(x, y, width, height, value, invert=False):
    """スロットルの位置を表示"""
    value = -value if invert else value
    
    # -1.0～1.0の値を0～1.0の範囲にマッピング
    normalized = (value + 1.0) / 2.0
    
    # バーを描画
    pygame.draw.rect(screen, (100, 100, 100), (x, y, width, height), 1)
    
    # 現在値を表示
    fill_height = int(height * normalized)
    pygame.draw.rect(screen, (100, 255, 100), (x + 2, y + height - fill_height - 2, width - 4, fill_height))

def draw_text(text, x, y, color=(255, 255, 255)):
    """テキストを描画"""
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

def get_axis_value(axis_id):
    """安全に軸の値を取得"""
    try:
        if joy and axis_id < joy.get_numaxes():
            return joy.get_axis(axis_id)
    except Exception as e:
        if show_debug and show_ui:
            print(f"軸 {axis_id} 取得エラー: {e}")
    return 0.0

def display_axis_config():
    """全ての軸の値を表示（設定モード用）"""
    if not joy:
        return
    
    # 背景を半透明にする
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    draw_text("--- 軸設定モード ---", WIDTH//2 - 80, 10, (255, 255, 0))
    draw_text("数字キー(0-9)を押して軸を選択し、対応する機能に割り当てます", 10, 40, (255, 200, 0))
    
    # 現在の割り当てを表示
    draw_text("現在の割り当て:", 10, 70, (200, 200, 200))
    draw_text(f"左X軸: {axis_mapping['lx']}", 20, 90)
    draw_text(f"左Y軸: {axis_mapping['ly']}", 20, 110)
    draw_text(f"右X軸: {axis_mapping['rx']}", 20, 130)
    draw_text(f"右Y軸: {axis_mapping['ry']} (スロットル軸)", 20, 150)
    
    # 全ての軸の値を表示
    draw_text("利用可能な軸:", WIDTH//2, 70, (200, 200, 200))
    num_axes = joy.get_numaxes()
    for i in range(min(num_axes, 10)):  # 最大10軸まで表示
        val = joy.get_axis(i)
        color = (255, 255, 0) if abs(val) > 0.5 else (255, 255, 255)
        draw_text(f"軸 {i}: {val:.2f}", WIDTH//2, 90 + i*20, color)
    
    draw_text("ESC: 終了  C: 設定モード終了  R: デフォルト設定に戻す", 10, HEIGHT - 30, (150, 150, 150))

# メインループ
running = True
selected_axis = None
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_d:
                show_debug = not show_debug
            elif event.key == pygame.K_v:
                show_values = not show_values
            elif event.key == pygame.K_a:
                # aキーでUI表示を切り替え（スティックは常に表示）
                show_ui = not show_ui
                show_all_axes = False  # UIを非表示にする場合、全軸表示も無効に
            elif event.key == pygame.K_s:
                # sキーで全軸表示のみを切り替え
                if show_ui:  # UIが表示されている場合のみ切り替え可能
                    show_all_axes = not show_all_axes
            elif event.key == pygame.K_c:
                config_mode = not config_mode
            elif event.key == pygame.K_r and config_mode:
                # デフォルト設定に戻す
                axis_mapping = default_axis_mapping.copy()
            
            # 設定モードでの軸選択
            if config_mode:
                if pygame.K_0 <= event.key <= pygame.K_9:
                    axis_num = event.key - pygame.K_0
                    if selected_axis is None:
                        selected_axis = axis_num
                        print(f"軸 {axis_num} を選択しました。割り当てる機能を選択してください:")
                        print("L: 左X, Y: 左Y, R: 右X, T: 右Y, S: スロットル")
                    elif joy and axis_num < joy.get_numaxes():
                        print(f"軸 {axis_num} を選択しました（無効な選択）")
                
                # 選択した軸の割り当て
                if selected_axis is not None:
                    if event.key == pygame.K_l:
                        axis_mapping["lx"] = selected_axis
                        print(f"軸 {selected_axis} を左Xに割り当てました")
                        selected_axis = None
                    elif event.key == pygame.K_y:
                        axis_mapping["ly"] = selected_axis
                        print(f"軸 {selected_axis} を左Yに割り当てました")
                        selected_axis = None
                    elif event.key == pygame.K_r:
                        if config_mode and selected_axis is not None:
                            axis_mapping["rx"] = selected_axis
                            print(f"軸 {selected_axis} を右Xに割り当てました")
                            selected_axis = None
                        elif config_mode:
                            # デフォルト設定に戻す
                            axis_mapping = default_axis_mapping.copy()
                            print("設定をデフォルトに戻しました")
                    elif event.key == pygame.K_t:
                        axis_mapping["ry"] = selected_axis
                        print(f"軸 {selected_axis} を右Yに割り当てました")
                        selected_axis = None

    screen.fill(CHROMA_COLOR)
    
    if joy:
        # 各軸の値を取得
        lx = get_axis_value(axis_mapping["lx"])
        ly = get_axis_value(axis_mapping["ly"])
        rx = get_axis_value(axis_mapping["rx"])
        ry = get_axis_value(axis_mapping["ry"])
        
        # スティック表示 - 常に表示（サイズを大きく、位置を調整）
        draw_stick(WIDTH - WIDTH//3, HEIGHT//2, STICK_SIZE, lx, ly, invert["lx"], invert["ly"])
        draw_stick(WIDTH//3, HEIGHT//2, STICK_SIZE, rx, ry, invert["rx"], invert["ry"])
        
        # スティックの方向を示すラベル（UIが非表示でも表示）
        draw_text("LEFT", WIDTH - WIDTH//3, HEIGHT//2 - STICK_SIZE//2 - 30, (200, 200, 200))
        draw_text("RIGHT", WIDTH//3, HEIGHT//2 - STICK_SIZE//2 - 30, (200, 200, 200))
        
        # UIが表示ONの場合だけ、値などを表示
        if show_ui:
            # 軸の値の表示
            if show_values:
                draw_text(f"RX: {lx:.2f}", 10, 10)
                draw_text(f"RY: {ly:.2f}", 10, 30)
                draw_text(f"LX: {rx:.2f}", 10, 50)
                draw_text(f"LY: {ry:.2f}", 10, 70)
            
            # 全ての軸の値を表示
            if show_all_axes:
                for i in range(joy.get_numaxes()):
                    val = joy.get_axis(i)
                    draw_text(f"軸 {i}: {val:.2f}", WIDTH - 120, 10 + i*20, (200, 200, 200))
            
            # デバッグ情報
            if show_debug:
                draw_text(f"コントローラー: {joy.get_name()}", 10, HEIGHT - 60, (200, 200, 0))
                draw_text(f"軸の数: {joy.get_numaxes()}", 10, HEIGHT - 40, (200, 200, 0))
                draw_text(f"ボタンの数: {joy.get_numbuttons()}", 10, HEIGHT - 20, (200, 200, 0))
                
            # 操作ガイド
            guide_text = "ESC: 終了  D: デバッグ表示  V: 値表示  A: UI表示切替  S: 全軸表示  C: 設定モード"
            draw_text(guide_text, 10, HEIGHT - 80, (150, 150, 150))
    else:
        # コントローラーが接続されていない場合
        draw_text("コントローラーが接続されていません", WIDTH // 2 - 150, HEIGHT // 2, (255, 0, 0))
        draw_text("コントローラーを接続して再起動してください", WIDTH // 2 - 180, HEIGHT // 2 + 30, (255, 0, 0))
    
    # 設定モードならオーバーレイ表示
    if config_mode:
        display_axis_config()
    
    pygame.display.update()
    clock.tick(60)

pygame.quit()
sys.exit()