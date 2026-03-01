from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # --- Private Room Flow ---
    print("=== Testing Private Room Flow ===")
    
    # Client 1
    context1 = browser.new_context()
    page1 = context1.new_page()
    
    # Dialog handler for Create Room (Name prompt, then confirm public/private)
    dialog_idx1 = 0
    def handle_create_private(dialog):
        global dialog_idx1
        print(f"Dialog {dialog_idx1}: {dialog.type} - {dialog.message}")
        try:
            if dialog_idx1 == 0:
                dialog.accept("AdminUser")
            elif dialog_idx1 == 1:
                dialog.accept("My Private Room")
            elif dialog_idx1 == 2:
                # Cancel the confirm() dialog -> Private
                dialog.dismiss()
        except BaseException as e:
            # Prevent hanging if playright complains abt async handles
            pass
        finally:
            dialog_idx1 += 1
            
    page1.on("dialog", handle_create_private)
    page1.goto('http://127.0.0.1:5001/')
    page1.wait_for_timeout(1000)
    
    page1.click('button:has-text("ルームを作成")')
    page1.wait_for_selector('#waitingStateContainer', state='visible')
    page1.wait_for_timeout(1000)
    
    # Extract the room ID so Client 2 can join
    room_id_text = page1.locator('#waitingRoomIdDisplay').inner_text()
    if not room_id_text:
        print("FAILED: No room id display found.")
        exit(1)
        
    print(f"Admin sees: {room_id_text}")
    private_room_id = room_id_text.split("ルームID: ")[1].split(" ")[0].strip()
    print(f"Extracted Private Room ID: {private_room_id}")
    
    # Client 2
    context2 = browser.new_context()
    page2 = context2.new_page()
    
    dialog_idx2 = 0
    def handle_join_private(dialog):
        global dialog_idx2
        print(f"Join Dialog {dialog_idx2}: {dialog.type} - {dialog.message}")
        if dialog_idx2 == 0:
            dialog.accept("PlayerTwo")
        elif dialog_idx2 == 1:
            dialog.accept(private_room_id)
        dialog_idx2 += 1
        
    page2.on("dialog", handle_join_private)
    page2.goto('http://127.0.0.1:5001/')
    page2.wait_for_timeout(1000)
    
    page2.click('button:has-text("プライベートルームに参加")')
    page2.wait_for_selector('#waitingStateContainer', state='visible')
    
    print("SUCCESS: Player 2 joined the private room via ID.")
    
    # Close 
    context1.close()
    context2.close()
    
    # --- Public Room Flow ---
    print("\n=== Testing Public Room Flow ===")
    
    context3 = browser.new_context()
    page3 = context3.new_page()
    
    dialog_idx3 = 0
    def handle_create_public(dialog):
        global dialog_idx3
        if dialog_idx3 == 0:
            dialog.accept("AdminPub")
        elif dialog_idx3 == 1:
            dialog.accept("My Public Room")
        elif dialog_idx3 == 2:
            # Accept the confirm() dialog -> Public
            dialog.accept()
        dialog_idx3 += 1
            
    page3.on("dialog", handle_create_public)
    page3.goto('http://127.0.0.1:5001/')
    page3.wait_for_timeout(1000)
    
    page3.click('button:has-text("ルームを作成")')
    page3.wait_for_selector('#waitingStateContainer', state='visible')
    page3.wait_for_timeout(1000)
    
    room_id_text_pub = page3.locator('#waitingRoomIdDisplay').inner_text()
    print(f"AdminPub sees: {room_id_text_pub}")
    if "パブリック" not in room_id_text_pub:
        print("FAILED: Room is not public.")
        exit(1)
        
    context4 = browser.new_context()
    page4 = context4.new_page()
    
    dialog_idx4 = 0
    def handle_join_public(dialog):
        global dialog_idx4
        if dialog_idx4 == 0:
            dialog.accept("PlayerPublic")
        dialog_idx4 += 1
            
    page4.on("dialog", handle_join_public)
    page4.goto('http://127.0.0.1:5001/')
    page4.wait_for_timeout(1000)
    
    page4.click('button:has-text("パブリックルームに参加")')
    page4.wait_for_selector('#waitingStateContainer', state='visible')
    
    print("SUCCESS: Player joined the public room automatically.")

    browser.close()
    print("\nALL INTEGRATION TESTS PASSED.")
