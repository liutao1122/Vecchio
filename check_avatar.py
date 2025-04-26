from supabase import create_client
import os

# Supabase配置
url = "https://rwlziuinlbazgoajkcme.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3bHppdWlubGJhemdvYWprY21lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxODAwNjIsImV4cCI6MjA2MDc1NjA2Mn0.Y1KiIiUXmDiDSFYFQLHmyd1Oe86SxSfvHJcKrJmz2gI"

try:
    # 创建 Supabase 客户端
    supabase = create_client(url, key)
    
    # 检查 trader_profiles 表
    print("\n检查 trader_profiles 表:")
    profile_response = supabase.table('trader_profiles').select('*').execute()
    if profile_response.data:
        for profile in profile_response.data:
            print(f"ID: {profile.get('id')}")
            print(f"头像URL: {profile.get('profile_image_url')}")
    else:
        print("trader_profiles 表中没有数据")
    
    # 检查 avatar_history 表
    print("\n检查 avatar_history 表:")
    avatar_response = supabase.table('avatar_history').select('*').order('created_at', desc=True).execute()
    if avatar_response.data:
        for avatar in avatar_response.data:
            print(f"用户ID: {avatar.get('user_id')}")
            print(f"图片URL: {avatar.get('image_url')}")
            print(f"是否当前: {avatar.get('is_current')}")
            print("---")
    else:
        print("avatar_history 表中没有数据")

except Exception as e:
    print(f"发生错误: {str(e)}") 