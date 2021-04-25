var cy = cytoscape({
    container: document.getElementById('cy'), // container to render in
    elements: [],
    style: [ // the stylesheet for the graph
      {
        selector: 'node',
        style: {
          'width': '80px',
          'height': '80px',
          'background-fit': 'contain',
          'background-color': 'hsl(0, 0%, 90%)',
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 3,
          'line-color': 'hsl(0, 0%, 70%)',
          'opacity': 0.2,
        }
      },
      {
          selector: '.selectedNode',
          style :{
              'border-width': 2,
              'border-color': 'black',
              'border-style': 'solid',
              'width': '95px',
              'height': '95px',
          }
      },
      {
          selector: '.selectedEdge',
          style: {

          }
      }
    ],
  
});

// let savedLayouts = {}
// let prevOption = getSelectedOption()

function getSelectedOption(){
    for (let el of document.querySelectorAll("input")){
        if (el.checked) {
            return el.value
        }
    }
}

// function storeLayout() {
//     const data = cy.json();
//     const nodes = data.elements.nodes
//     const savedLayouts = {};
//     for (let n of nodes) {
//       savedLayouts[n.data.id] = n.position;
//     }
//     savedLayouts['pan'] = data.pan
//     savedLayouts['zoom'] = data.zoom
//     return savedLayouts;
// }

function gcd(a, b){
    if (!b) {
      return a;
    }  
    return gcd(b, a % b);
}

function lcm(a, b){
    return a * b / gcd(a, b)
}

function rotate(pos, center, angle){
    let dx = pos.x - center.x
    let dy = pos.y - center.y
    let r = Math.sqrt(dx**2 + dy**2)
    let theta = Math.atan2(dy, dx) + angle // in radian
    let newX = center.x + r * Math.cos(theta)
    let newY = center.y + r * Math.sin(theta)
    return {x: newX, y: newY}
}

function rotateCirles(){
    const selectedNode = cy.$('.selectedNode')
    let levelFolds = {}
    for (let n of cy.$('node')) {
        // ignore 0 connection ones
        let l = selectedNode.edgesWith(n).length
        if (l > 0) {
            if (!levelFolds[l]) {
                levelFolds[l] = 1
            } else {
                levelFolds[l] += 1
            }
        }
    }

    let folds = Object.values(levelFolds).map(x => parseInt(x)).sort((a, b) => a - b)
    let maxFold = folds[folds.length - 1]
    // levels2Rotate
    for (let n of cy.nodes()) {
        let l = selectedNode.edgesWith(n).length
        let currentFold = levelFolds[l]
        if (currentFold < maxFold){
            if (currentFold == folds[folds.length - 2]){
                let angle = 2 * Math.PI / lcm(currentFold, maxFold)
            }
            if (currentFold == folds[folds.length - 3]){
                let angle = 2 * Math.PI / lcm(currentFold, maxFold)
            }
            
            
            n.animate({
                position: rotate(n.position(),selectedNode.position(),angle),
                queue: false,
                duration: 600,
                easing: 'ease-in-out',
            })
        }
                            
    }
}

function getLayout(name){
    let layoutOptions = {
        name: name,
        animate: "end",
        animationEasing: 'ease-in-out',
        animationDuration: 800,
        stop: function(){
            // prevOption = getSelectedOption()
        },
    }
    let extraOptions = {}
    if (name == 'fcose') {
        extraOptions =  {
            nodeSeparation: 150,
            nodeRepulsion: node => 100000, // node => 4500
            idealEdgeLength: edge => 100,
            edgeElasticity: edge => 0.2,
        }
    }
    if (name == 'avsdf') {
        extraOptions =  {
            nodeSeparation: 95,
        }
    }
    if (name == 'concentric') {
        extraOptions = {
            concentric: function (node) {
                let selectedNode = cy.$('.selectedNode')
                if (selectedNode.id() == node.id()) {
                    return 9
                }
                else {

                    return selectedNode.edgesWith(node).length
                }
            },
            levelWidth: n => 1,
            // spacingFactor: 1.2,
            startAngle: Math.random() * 2 * Math.PI,
            stop: rotateCircles
            // transform: function (node, position) {

            //     if (node.id()=='甘雨'){
            //         console.log(position)
            //         return {x: position.x+100, y: position.y}
            //     }
            //     return position
            // }
        }
        
    }
    // if (name == 'preset') {
    //     let sl = savedLayouts[params.layoutName]
    //     console.log(sl)
    //     extraOptions =  {
    //         pan: sl['pan'],
    //         zoom: sl['zoom'],
    //         positions: node => sl[node.id]
    //     }
    // }
    return cy.layout({...layoutOptions, ...extraOptions})
}

function setLayout(name, overwrite=false) {
    // reuse saved layout
    // (!overwrite && savedLayouts[name]) ? getLayout('preset', {layoutName: name}) : 
    let layout = getLayout(name)
    layout.run()
}

function showPopup(myContent){
    let dummyDomEle = document.createElement('div');

    let tip = tippy(dummyDomEle, { 
    trigger: 'manual', 
    followCursor: 'initial',
    arrowType: 'round',    
    theme: 'light-border',

    content: () => {
            let content = document.createElement('div');
            content.innerHTML = myContent;
            return content;
            }
    });

    tip.show();
}

async function getJson(url) {
    let response = await fetch(url);
    let data = await response.json()
    return data;
}

var charData;
var charNames = [];

async function main() {
    charData = await getJson('char_data.json')

    for (const char of charData) {
        if (char.name != '旅行者') {
            charNames.push(char.name)
            cy.add({
                group: 'nodes',
                data: { id: char.name },
                style: {
                    'background-image': `./images/${char.name}.png`
                    }
            })
        }
    }

    for (const sourceChar of charData) {
        for (const target of charNames) {
            for (const title in sourceChar.lines) {
                if (title.includes(target) && target != sourceChar.name) {
                    cy.add({
                        group: 'edges',
                        data: {
                            id: sourceChar.name + title, 
                            source: sourceChar.name, 
                            target: target,
                            content: `${sourceChar.name + title}：` + sourceChar.lines[title]
                        }
                    })
                }
            }
        }
    }

    setLayout(getSelectedOption())

    cy.$('node').on('tap', function(evt){
        let selectedNode = evt.target;
        console.log(selectedNode.id())
        if (! selectedNode.hasClass('selectedNode')){
            cy.$('node').removeClass('selectedNode')
            selectedNode.addClass('selectedNode')
            cy.$('edge').removeClass('selectedEdge')
            let selectedEdges = selectedNode.connectedEdges()
            selectedEdges.on('tap', function(evt){
                showPopup()
            })
        }
        if (document.querySelector('input[type=checkbox]').checked) {
            setLayout('concentric')
        }
    });

}

main();

document.querySelectorAll("input[type=radio]").forEach(r => {
    r.addEventListener('input', function(e){
        // savedLayouts[prevOption] = storeLayout()
        setLayout(e.target.value)
    })
})

document.querySelector("#refreshGraph").onclick = function(e){
    setLayout(getSelectedOption(), true)
}