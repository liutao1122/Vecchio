// 示例数据
const leaderboardData = [
    {
        avatar: 'https://via.placeholder.com/50',
        profit: '¥12,345',
        fans: '10,000',
        likes: '5,678'
    },
    {
        avatar: 'https://via.placeholder.com/50',
        profit: '¥10,987',
        fans: '8,765',
        likes: '4,321'
    },
    {
        avatar: 'https://via.placeholder.com/50',
        profit: '¥9,876',
        fans: '7,654',
        likes: '3,456'
    },
    {
        avatar: 'https://via.placeholder.com/50',
        profit: '¥8,765',
        fans: '6,543',
        likes: '2,345'
    },
    {
        avatar: 'https://via.placeholder.com/50',
        profit: '¥7,654',
        fans: '5,432',
        likes: '1,234'
    }
];

// 获取排行榜列表容器
const leaderboardList = document.getElementById('leaderboardList');

// 渲染排行榜
function renderLeaderboard() {
    leaderboardList.innerHTML = '';
    
    leaderboardData.forEach((item, index) => {
        const rank = index + 1;
        const rankClass = `rank-${rank}`;
        
        const leaderboardItem = document.createElement('div');
        leaderboardItem.className = 'leaderboard-item';
        
        leaderboardItem.innerHTML = `
            <div class="rank ${rankClass}">${rank}</div>
            <div class="avatar">
                <img src="${item.avatar}" alt="用户头像">
            </div>
            <div class="profit">${item.profit}</div>
            <div class="fans">${item.fans}</div>
            <div class="likes">${item.likes}</div>
        `;
        
        leaderboardList.appendChild(leaderboardItem);
    });
}

// 初始化排行榜
renderLeaderboard(); 