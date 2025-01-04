**[king-of-infinite-space.github.io/genshin-social-network](https://king-of-infinite-space.github.io/genshin-social-network/)**

---

以游戏《原神》(Genshin Impact)中的人物为例制作的社交网络图。以人物为顶点，若人物A语音中有关于人物B的条目，添加A→B的边。\
A social network graph of Genshin characters. Each node is a character and each edge from A to B is a voice line of character A about character B.

#### 布局说明 | About layouts

本项目使用[Cytoscape.js](https://js.cytoscape.org/)生成网络图。采用了以下布局。\
This project uses __ to generate network graph. The following layouts are used.

- [fcose](https://github.com/iVis-at-Bilkent/cytoscape.js-fcose)：基于力导向算法。（进行力学模拟，顶点互相排斥，边提供张力，直至平衡。）Based on force-directed layout. Nodes repel each other and edges pull them together. The forces are simulated until equilibrium is reached.

- [avsdf](https://github.com/iVis-at-Bilkent/cytoscape.js-avsdf)：在圆周上排列顶点，使得边的交叉尽可能少。The nodes are distributed along a circle such that the crossing of edges is minimized.

- custom：同心圆布局。初始状态下边越多的顶点越靠近中心。选中人物后以其为中心，与之连接越多的人物越靠近中心。A concentric layout. Initially, nodes with more edges are closer to the center. When a character is selected, it moves to the center and nodes with more edges with it are closer.

#### 探索此图 | Explore the graph

`cy` 变量是Cytoscape.js图的对象。`stats`变量包含了每个节点的统计数字。可在控制台进行探索。\
`cy` is the variable for Cytoscape.js graph object. `stats` includes some statistics of nodes. Feel free to explore them in the console.


#### 版权声明 | Copyright disclaimer

本项目仅用于演示和研究目的。游戏内容版权归mihoyo所有。\
This project is for demonstration and research purpose only. Copyright holder of game data is mihoyo.

---

##### 作者声明 | Personal notice
本人并非该游戏玩家，只是“云玩家”。抵制氪金游戏从我做起。\
I don't even play this game (only read and watch the stories). I'm against gacha games.

##### 类似项目 | Similar project
[CaoMeiYouRen/genshin-relation-graph: 原神人物关系图](https://github.com/CaoMeiYouRen/genshin-relation-graph)

##### 原神相关百科网站 | Genshin wikis
[原神WIKI_玩家共建原神百科-BWIKI_哔哩哔哩](https://wiki.biligame.com/ys/%E9%A6%96%E9%A1%B5)\
[旅行者创作平台-观测枢-原神wiki-米游社](https://bbs.mihoyo.com/ys/obc/)\
[原神 - 萌娘百科 万物皆可萌的百科全书](https://zh.moegirl.org.cn/%E5%8E%9F%E7%A5%9E)\
[Genshin Impact Wiki | Fandom](https://genshin-impact.fandom.com/wiki/Genshin_Impact_Wiki)\
[Honey Impact | Honey Impact - Genshin Impact DB and Tools](https://genshin.honeyhunterworld.com/) (multi-language | 多语言)\
[Genshin DB - Genshin Impact Database](https://genshindb.org/)\
[Genshin Impact Characters List - Genshin.gg Wiki Database](https://genshin.gg/)

##### Github上的其他原神相关项目（仅供参考） | Other Genshin related projects on Github (for reference only)
[Dimbreath/GenshinData: Repository containing the game data for the game Genshin Impact.](https://github.com/Dimbreath/GenshinData)\
[uzair-ashraf/genshin-impact-wish-simulator: A React web application to simulate Genshin Impact gacha in the browser](https://github.com/uzair-ashraf/genshin-impact-wish-simulator)\
[GenshinMap/genshinmap.github.io: A flexible, community-driven interactive map for Genshin Impact.](https://github.com/GenshinMap/genshinmap.github.io)

<img src='https://count.lnfinite.space/repo/genshin-social-network.svg?plus=1' width='0' height='0' />