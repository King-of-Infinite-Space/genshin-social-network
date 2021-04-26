var cy = cytoscape({
    container: document.getElementById('cy'), // container to render in
    boxSelectionEnabled: false,
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
          'line-color': 'hsl(0, 0%, 75%)',
          'opacity': 0.25,
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
            'line-color': 'hsl(0, 0%, 45%)',
            'width': 4,
            'opacity': 0.3,
          }
      },
      {
        selector: '.unselectedEdge',
        style: {
          'line-color': 'hsl(0, 0%, 85%)',
          'width': 2,
          'opacity': 0.15,
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

function rotateCircles(){
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
    let maxFold2 = folds[folds.length - 2]
    let levelRef = Object.keys(levelFolds).filter(k => levelFolds[k] == maxFold)[0];
    for (let n of cy.nodes()) {
        let l = selectedNode.edgesWith(n).length
        let currentFold = levelFolds[l]
        if (l != levelRef && l > 0){
            let angle = 0
            if (folds.indexOf(currentFold) == folds.length - 2){
                angle = Math.PI / lcm(currentFold, maxFold)
            }
            else if (folds.indexOf(currentFold) == folds.length - 3){
                if (maxFold == maxFold2) {
                    angle = 0.5 * Math.PI / maxFold
                }                
                else {
                    angle = - Math.PI / maxFold
                }
            }
            // else if (folds.indexOf(currentFold) == folds.length - 4){
            //     angle = - Math.PI / maxFold
            // }
            else {
                angle = - Math.random() * Math.PI / maxFold
            }

            n.animate({
                position: rotate(n.position(),selectedNode.position(), angle),
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
            // randomize: false,
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
            levelWidth: n => 1,
            concentric: function (node) {
                    let d = node.degree()
                    let n = 1 // n <= 12
                    if (d >= 13) n += 1
                    if (d >= 16) n += 1
                    if (d >= 20) n += 1
                    // 1, 2, (3, 4)
                    // l = Math.min(l, 3)
                    return n
            }
        }
    }
    if (name == 'concentricCustom') {
        extraOptions = {
            name: 'concentric',
            concentric: function (node) {
                let selectedNode = cy.$('.selectedNode')
                if (selectedNode.id() == node.id()) {
                    return 9
                }
                else {
                    let l = selectedNode.edgesWith(node).length
                    // 1, 2, (3, 4)
                    // l = Math.min(l, 3)
                    return l
                }
            },
            levelWidth: n => 1,
            // equidistant: true,
            // spacingFactor: 0.5,
            startAngle: Math.random() * 2 * Math.PI,
            stop: function(){
                rotateCircles()
            }
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
    if (name == 'concentric' && cy.$('.selectedNode').length > 0){
        name = 'concentricCustom'
    }
    let layout = getLayout(name)
    layout.run()
}

function unselectElements(){
    cy.$('node').removeClass('selectedNode')
    cy.$('edge').removeClass('unselectedEdge')
    cy.$('edge').removeClass('selectedEdge')
}

function makeTippyContent(node1, node2){
    let text = ''
    for (const edge of node1.edgesTo(node2)){
        text += `<div class="tip-title">${edge.data().title}</div>`
        text += `<div class="tip-quote">${edge.data().content}</div>`
    }
    if (text && node2.edgesTo(node1).length > 0) text += '<div class="tip-spacing"></div>'
    for (const edge of node2.edgesTo(node1)){
        text += `<div class="tip-title">${edge.data().title}</div>`
        text += `<div class="tip-quote">${edge.data().content}</div>`
    }
    return text
}

function makeTippy(ele, text){
    var ref = ele.popperRef();

    // Since tippy constructor requires DOM element/elements, create a placeholder
    var dummyDomEle = document.createElement('div');

    var tip = tippy( dummyDomEle, {
        getReferenceClientRect: ref.getBoundingClientRect,
        trigger: 'manual', // mandatory
        // dom element inside the tippy:
        content: function(){ // function can be better for performance
            var div = document.createElement('div');

            div.innerHTML = text;

            return div;
        },
        // your own preferences:
        onHidden(instance) {
            instance.destroy();
        },
        delay: [100, null],
        theme: 'light',
        arrow: true,
        placement: 'auto',
        hideOnClick: true,
        sticky: "reference",

        // if interactive:
        interactive: true,
        appendTo: document.body // or append dummyDomEle to document.body
    } );

    return tip;
};

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
                if (title.includes('关于'+target) && target != sourceChar.name) {
                    cy.add({
                        group: 'edges',
                        data: {
                            id: sourceChar.name + title,  // A关于B
                            source: sourceChar.name, 
                            target: target,
                            title: sourceChar.name + title,
                            content: sourceChar.lines[title]
                        }
                    })
                }
            }
        }
    }

    for (const n of cy.$('node')){
        if (n.degree() == 0){
            n.remove()
        }
    }

    setLayout(getSelectedOption())

    cy.$('edge').unpanify()
    cy.$('edge').unselectify()

    cy.on('tap', 'node', function(event){       
        var target = event.target;
        if (!target.hasClass('selectedNode')){
            cy.$('node').removeClass('selectedNode')
            target.addClass('selectedNode')
            cy.$('edge').addClass('unselectedEdge')
            let targetEdges = target.connectedEdges()
            targetEdges.removeClass('unselectedEdge')
            targetEdges.addClass('selectedEdge')

            if (getSelectedOption() == 'concentric'){
                setLayout('concentricCustom')
            }
        }
    })

    cy.on('tap',function(ev){
        if (ev.target === cy){ // tap bg
                unselectElements()
        }
    })

    cy.$('edge').on('mouseover', function(event) {
        let targetEdge = event.target
        if (targetEdge.hasClass('selectedEdge')){     
            targetEdge.addClass('showingTip')     
            let node1 = cy.$('.selectedNode')
            let node2 = targetEdge.source().id() == node1.id() ? targetEdge.target() : targetEdge.source()
            let text = makeTippyContent(node1, node2)
            // console.log(text);
            targetEdge.tippy = makeTippy(targetEdge, text)
            targetEdge.tippy.show()
            console.log('tippy')
            targetEdge.on('mouseout', () => {
                targetEdge.tippy.hide();
            });
        }
    })
}

main();

document.querySelectorAll("input[type=radio]").forEach(r => {
    r.addEventListener('input', function(e){
        // savedLayouts[prevOption] = storeLayout()
        setLayout(e.target.value)
    })
})

document.querySelector("#refreshGraph").onclick = function(e){
    // unselectElements()
    setLayout(getSelectedOption(), true)
}