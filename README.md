### 原神人物关系网络图

—> king-of-infinite-space.github.io/genshin-social-network <—

a social network graph of Genshin characters

以游戏《原神》(Genshin Impact)中的人物为例制作的社交网络图。以人物为顶点，若人物A语音中有关于人物B的条目，则添加A→B的边。

#### 布局说明

本项目使用[Cytoscape.js](https://js.cytoscape.org/)生成网络图。采用了以下布局：

- [fcose](https://github.com/iVis-at-Bilkent/cytoscape.js-fcose)：基于力导向算法（进行力学模拟，顶点互相排斥，边提供张力，直至平衡）

- [avsdf](https://github.com/iVis-at-Bilkent/cytoscape.js-avsdf)：在圆周上排列顶点，使得边的交叉尽可能少

- 自定义：同心圆布局。初始状态下边越多的顶点越靠近中心。选中人物后以其为中心，与之连接越多的人物越靠近中心


#### 版权声明

本项目仅用于演示目的。文本和图像通过MediaWiki API获取于[原神WIKI_玩家共建原神百科-BWIKI_哔哩哔哩](https://wiki.biligame.com/ys/%E9%A6%96%E9%A1%B5)（CC BY-NC-SA协议）。游戏内容版权归mihoyo所有。

---
##### 作者声明
本人并非该游戏玩家，只是“云玩家”。抵制氪金游戏人人有责。

##### 其他原神相关百科网站
[旅行者创作平台-观测枢-原神wiki-米游社](https://bbs.mihoyo.com/ys/obc/)
[原神 - 萌娘百科 万物皆可萌的百科全书](https://zh.moegirl.org.cn/%E5%8E%9F%E7%A5%9E)
[Genshin Impact Wiki | Fandom](https://genshin-impact.fandom.com/wiki/Genshin_Impact_Wiki)
[Honey Impact | Honey Impact - Genshin Impact DB and Tools](https://genshin.honeyhunterworld.com/) (multi-language / 多语言)

##### Other Genshin related projects on Github (there are many)
[Dimbreath/GenshinData: Repository containing the game data for the game Genshin Impact.](https://github.com/Dimbreath/GenshinData)
[uzair-ashraf/genshin-impact-wish-simulator: A React web application to simulate Genshin Impact gacha in the browser](https://github.com/uzair-ashraf/genshin-impact-wish-simulator)
[GenshinMap/genshinmap.github.io: A flexible, community-driven interactive map for Genshin Impact.](https://github.com/GenshinMap/genshinmap.github.io)