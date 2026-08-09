/**
 * 光明 L0 核心字趣味学习 - 游戏逻辑 v4.0
 */

// ==================== L0 核心字数据 ====================
const L0_CHARS = [
    {
        char: '设',
        pinyin: 'shè',
        meaning: '变量定义',
        desc: '声明一个变量，类似其他语言的 let/var。',
        example: '设 甲 为 10',
        category: '基础',
        tip: '「设 变量名 为 值」是最常用的变量定义方式。'
    },
    {
        char: '为',
        pinyin: 'wéi',
        meaning: '赋值',
        desc: '将值赋给变量，或用于比较中的「等于」。',
        example: '设 姓名 为 "小明"',
        category: '基础',
        tip: '「为」既可以用于赋值，也可以用于比较。'
    },
    {
        char: '若',
        pinyin: 'ruò',
        meaning: '条件判断',
        desc: '如果条件成立，则执行对应的代码块。',
        example: '若 甲 > 5 则：\n  打印("成立")',
        category: '控制流',
        tip: '「若 条件 则：」是 if 语句的光明写法。'
    },
    {
        char: '则',
        pinyin: 'zé',
        meaning: '那么/则',
        desc: '与「若」配合使用，表示条件成立时执行。',
        example: '若 甲 > 0 则：\n  打印("正数")',
        category: '控制流',
        tip: '「则」必须与「若」配对使用，不能单独出现。'
    },
    {
        char: '否',
        pinyin: 'fǒu',
        meaning: '否则',
        desc: '条件不成立时执行的代码块，与「若」配对。',
        example: '若 甲 > 0 则：\n  打印("正数")\n否：\n  打印("非正数")',
        category: '控制流',
        tip: '「否」相当于 else，可以单独使用也可以接「或若」。'
    },
    {
        char: '遍',
        pinyin: 'biàn',
        meaning: '遍历循环',
        desc: '遍历列表或可迭代对象中的每个元素。',
        example: '遍 元素 之 列表：\n  打印(元素)',
        category: '控制流',
        tip: '「遍 变量 之 集合：」是 for-each 循环。'
    },
    {
        char: '当',
        pinyin: 'dāng',
        meaning: '条件循环',
        desc: '当条件满足时重复执行代码块，类似 while。',
        example: '当 甲 < 10：\n  甲 = 甲 + 1',
        category: '控制流',
        tip: '「当 条件：」循环，小心不要写成死循环！'
    },
    {
        char: '段',
        pinyin: 'duàn',
        meaning: '函数定义',
        desc: '定义一个函数（段落），可以接收参数和返回值。',
        example: '段 平方(x)：\n  返回 x * x',
        category: '函数',
        tip: '「段 函数名(参数)：」是光明定义函数的方式。'
    },
    {
        char: '返',
        pinyin: 'fǎn',
        meaning: '返回值',
        desc: '从函数中返回一个值，结束函数的执行。',
        example: '段 加倍(x)：\n  返 x * 2',
        category: '函数',
        tip: '「返」后面跟要返回的值，函数执行到此处结束。'
    },
    {
        char: '类',
        pinyin: 'lèi',
        meaning: '类定义',
        desc: '定义一个类，用于面向对象编程。',
        example: '类 动物：\n  段 叫()：\n    打印("...")',
        category: '面向对象',
        tip: '「类」可以定义属性和方法，支持继承。'
    },
    {
        char: '新',
        pinyin: 'xīn',
        meaning: '创建实例',
        desc: '创建一个类的实例对象，类似 new。',
        example: '设 狗 为 新 动物()',
        category: '面向对象',
        tip: '「新」后面跟类名和构造参数。'
    },
    {
        char: '引',
        pinyin: 'yǐn',
        meaning: '引入/引用',
        desc: '引入外部代码或模块，如 Python 代码块。',
        example: '引 Python:\nimport math\n出 math',
        category: '模块',
        tip: '「引 Python:」可以嵌入 Python 代码，是 L4 层的关键。'
    },
    {
        char: '出',
        pinyin: 'chū',
        meaning: '导出/输出',
        desc: '从嵌入块中导出变量，或在 L4 中导出符号。',
        example: '引 Python:\nresult = 42\n出 result',
        category: '模块',
        tip: '「出」用于导出 Python 块中的变量供光明使用。'
    },
    {
        char: '且',
        pinyin: 'qiě',
        meaning: '逻辑与',
        desc: '逻辑与运算符，两个条件都成立时为真。',
        example: '若 甲 > 0 且 甲 < 10 则：',
        category: '逻辑',
        tip: '「且」相当于 &&，优先级高于「或」。'
    },
    {
        char: '或',
        pinyin: 'huò',
        meaning: '逻辑或',
        desc: '逻辑或运算符，两个条件有一个成立即为真。',
        example: '若 甲 < 0 或 甲 > 100 则：',
        category: '逻辑',
        tip: '「或」相当于 ||，优先级低于「且」。'
    },
    {
        char: '非',
        pinyin: 'fēi',
        meaning: '逻辑非',
        desc: '逻辑非运算符，取反一个布尔值。',
        example: '若 非 甲 则：\n  打印("甲为假")',
        category: '逻辑',
        tip: '「非」是一元运算符，放在表达式前面取反。'
    },
    {
        char: '真',
        pinyin: 'zhēn',
        meaning: '真值',
        desc: '布尔值 true，表示条件成立。',
        example: '设 完成 为 真',
        category: '基础',
        tip: '「真」和「假」是光明中的布尔字面量。'
    },
    {
        char: '假',
        pinyin: 'jiǎ',
        meaning: '假值',
        desc: '布尔值 false，表示条件不成立。',
        example: '设 完成 为 假',
        category: '基础',
        tip: '条件判断中，只有「假」和「空」被视为假值。'
    },
    {
        char: '空',
        pinyin: 'kōng',
        meaning: '空值',
        desc: '空值 null/none，表示什么都没有。',
        example: '设 结果 为 空',
        category: '基础',
        tip: '「空」表示无值，常用于函数返回或初始化。'
    }
];

// ==================== 游戏状态 ====================
let currentMode = 'learn';
let quizState = { questions: [], current: 0, correct: 0, wrong: 0 };
let matchState = { selected: null, pairs: 0, timer: 0, timerId: null, matched: {} };

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    renderCardGrid();
    initQuiz();
    initMatch();
});

// ==================== 模式切换 ====================
function switchMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.game-body').forEach(function(el) {
        el.classList.add('hidden');
    });
    document.getElementById('gameBodyLearn').classList.toggle('hidden', mode !== 'learn');
    document.getElementById('gameBodyQuiz').classList.toggle('hidden', mode !== 'quiz');
    document.getElementById('gameBodyMatch').classList.toggle('hidden', mode !== 'match');

    // 更新按钮状态
    document.querySelectorAll('.game-mode-btn').forEach(function(btn) {
        btn.classList.remove('active');
    });
    var btnMap = { learn: 'modeLearnBtn', quiz: 'modeQuizBtn', match: 'modeMatchBtn' };
    var activeBtn = document.getElementById(btnMap[mode]);
    if (activeBtn) activeBtn.classList.add('active');

    // 更新进度条
    updateProgressBar();
}

// ==================== 学习模式 ====================
function renderCardGrid() {
    var grid = document.getElementById('cardGrid');
    if (!grid) return;

    var html = '';
    L0_CHARS.forEach(function(item) {
        html += '<div class="l0-card" onclick="showDetail(\'' + item.char + '\')">';
        html += '<div class="l0-card-char">' + item.char + '</div>';
        html += '<div class="l0-card-pinyin">' + item.pinyin + '</div>';
        html += '<div class="l0-card-meaning">' + item.meaning + '</div>';
        html += '<div class="l0-card-category">' + item.category + '</div>';
        html += '</div>';
    });
    grid.innerHTML = html;
}

// ==================== 详情弹窗 ====================
function showDetail(charName) {
    var item = L0_CHARS.find(function(c) { return c.char === charName; });
    if (!item) return;

    var overlay = document.getElementById('detailOverlay');
    var content = document.getElementById('detailContent');

    content.innerHTML = '<div class="detail-big-char">' + item.char + '</div>' +
        '<div class="detail-pinyin">' + item.pinyin + '</div>' +
        '<div class="detail-meaning">' + item.meaning + '</div>' +
        '<div class="detail-category-badge">' + item.category + '</div>' +
        '<div class="detail-section"><h4>📖 说明</h4><p>' + item.desc + '</p></div>' +
        '<div class="detail-section"><h4>💡 小贴士</h4><p>' + item.tip + '</p></div>' +
        '<div class="detail-section"><h4>📝 示例代码</h4><pre>' + item.example + '</pre></div>' +
        '<button class="btn btn-try" onclick="tryInPlayground(\'' + item.char + '\')">🚀 在 Playground 中试试</button>';

    overlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeDetail() {
    document.getElementById('detailOverlay').classList.add('hidden');
    document.body.style.overflow = '';
}

function tryInPlayground(charName) {
    var item = L0_CHARS.find(function(c) { return c.char === charName; });
    if (!item) return;
    // 保存代码到 localStorage 并跳转到首页
    try {
        localStorage.setItem('light_playground_code', item.example + '\n');
    } catch (e) {}
    window.location.href = '/';
}

// 点击遮罩关闭详情
document.addEventListener('click', function(e) {
    var overlay = document.getElementById('detailOverlay');
    if (e.target === overlay) {
        closeDetail();
    }
});

// 键盘快捷键
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeDetail();
    }
});

// ==================== 闯关模式 ====================
function initQuiz() {
    quizState.questions = shuffleArray(L0_CHARS.slice());
    quizState.current = 0;
    quizState.correct = 0;
    quizState.wrong = 0;
    renderQuiz();
}

function renderQuiz() {
    if (quizState.current >= quizState.questions.length) {
        showQuizResult();
        return;
    }

    var item = quizState.questions[quizState.current];
    document.getElementById('quizCurrent').textContent = quizState.current + 1;
    document.getElementById('quizTotal').textContent = quizState.questions.length;
    document.getElementById('quizCorrect').textContent = quizState.correct;
    document.getElementById('quizWrong').textContent = quizState.wrong;

    // 随机选择 4 个选项（包含正确答案）
    var options = [item];
    var others = L0_CHARS.filter(function(c) { return c.char !== item.char; });
    var shuffledOthers = shuffleArray(others);
    for (var i = 0; i < 3 && i < shuffledOthers.length; i++) {
        options.push(shuffledOthers[i]);
    }
    options = shuffleArray(options);

    var questionEl = document.getElementById('quizQuestion');
    questionEl.innerHTML = '<div class="quiz-question-text">「' + item.char + '」的含义是什么？</div>' +
        '<div class="quiz-question-hint">该字属于 <strong>' + item.category + '</strong> 类别</div>';

    var optionsEl = document.getElementById('quizOptions');
    var html = '';
    options.forEach(function(opt) {
        html += '<div class="quiz-option" onclick="selectQuizOption(this, \'' + opt.char + '\', \'' + item.char + '\')">' +
            opt.meaning + '</div>';
    });
    optionsEl.innerHTML = html;

    document.getElementById('quizResult').classList.add('hidden');
    document.getElementById('quizResult').innerHTML = '';
    document.getElementById('quizNextBtn').classList.add('hidden');
}

function selectQuizOption(el, selectedChar, correctChar) {
    // 禁用所有选项
    document.querySelectorAll('.quiz-option').forEach(function(opt) {
        opt.style.pointerEvents = 'none';
    });

    var isCorrect = selectedChar === correctChar;
    if (isCorrect) {
        el.classList.add('correct');
        quizState.correct++;
    } else {
        el.classList.add('wrong');
        quizState.wrong++;
        // 高亮正确答案
        document.querySelectorAll('.quiz-option').forEach(function(opt) {
            var optChar = opt.getAttribute('onclick') ? 
                opt.getAttribute('onclick').match(/'([^']+)'/g) : null;
            if (optChar && optChar[1] && optChar[1].replace(/'/g, '') === correctChar) {
                // Can't easily match, use a different approach
            }
        });
    }

    // 找到并高亮正确答案
    document.querySelectorAll('.quiz-option').forEach(function(opt) {
        var clickAttr = opt.getAttribute('onclick') || '';
        var match = clickAttr.match(/'([^']+)'/g);
        if (match && match.length >= 3) {
            var optChar = match[1].replace(/'/g, '');
            if (optChar === correctChar) {
                opt.classList.add('correct');
            }
        }
    });

    var resultEl = document.getElementById('quizResult');
    resultEl.classList.remove('hidden');
    if (isCorrect) {
        var item = L0_CHARS.find(function(c) { return c.char === correctChar; });
        resultEl.innerHTML = '<div class="quiz-result-correct">✅ 正确！</div>' +
            '<div class="quiz-result-tip">' + (item ? item.tip : '') + '</div>';
    } else {
        var item = L0_CHARS.find(function(c) { return c.char === correctChar; });
        resultEl.innerHTML = '<div class="quiz-result-wrong">❌ 不对哦！正确答案是「' + correctChar + '」</div>' +
            '<div class="quiz-result-tip">' + (item ? item.desc : '') + '</div>';
    }

    document.getElementById('quizNextBtn').classList.remove('hidden');
    document.getElementById('quizNextBtn').textContent = 
        quizState.current >= quizState.questions.length - 1 ? '查看成绩 🎉' : '下一题 →';
}

function nextQuizQuestion() {
    quizState.current++;
    if (quizState.current >= quizState.questions.length) {
        showQuizResult();
    } else {
        renderQuiz();
    }
}

function showQuizResult() {
    var total = quizState.questions.length;
    var correct = quizState.correct;
    var score = Math.round((correct / total) * 100);
    var grade = score >= 90 ? '🏆 太棒了！' : (score >= 70 ? '👏 不错哦！' : (score >= 50 ? '💪 继续加油！' : '📚 再来一次！'));

    var questionEl = document.getElementById('quizQuestion');
    questionEl.innerHTML = '<div class="quiz-result-final">' + grade + '</div>';

    var optionsEl = document.getElementById('quizOptions');
    optionsEl.innerHTML = '<div class="quiz-final-stats">' +
        '<div class="quiz-final-stat">答对: <strong>' + correct + '</strong> / ' + total + '</div>' +
        '<div class="quiz-final-stat">得分: <strong>' + score + '</strong> 分</div>' +
        '<div class="quiz-final-stat">用时: —</div>' +
        '</div>' +
        '<button class="btn btn-retry" onclick="initQuiz()">🔄 再来一次</button>';

    document.getElementById('quizResult').classList.add('hidden');
    document.getElementById('quizNextBtn').classList.add('hidden');
}

// ==================== 连连看模式 ====================
function initMatch() {
    matchState.selected = null;
    matchState.pairs = 0;
    matchState.matched = {};
    if (matchState.timerId) {
        clearInterval(matchState.timerId);
        matchState.timerId = null;
    }
    matchState.timer = 0;
    document.getElementById('matchTimer').textContent = '0';
    document.getElementById('matchPairs').textContent = '0';
    document.getElementById('matchResult').innerHTML = '';
    document.getElementById('matchResult').classList.add('hidden');
    renderMatch();
}

function renderMatch() {
    var board = document.getElementById('matchBoard');
    if (!board) return;

    // 创建配对卡片：一半是字符，一半是含义
    var cards = [];
    L0_CHARS.forEach(function(item) {
        cards.push({ id: item.char + '_char', type: 'char', char: item.char, pairId: item.char });
        cards.push({ id: item.char + '_meaning', type: 'meaning', meaning: item.meaning, pairId: item.char });
    });
    cards = shuffleArray(cards);

    var html = '';
    cards.forEach(function(card) {
        var isMatched = matchState.matched[card.pairId];
        var cls = 'match-card';
        if (isMatched) cls += ' matched';
        if (card.type === 'char') {
            cls += ' match-card-char';
        } else {
            cls += ' match-card-meaning';
        }
        html += '<div class="' + cls + '" data-id="' + card.id + '" data-pair="' + card.pairId + '" data-type="' + card.type + '" onclick="selectMatchCard(this)">';
        if (card.type === 'char') {
            html += '<span class="match-card-char-text">' + card.char + '</span>';
        } else {
            html += '<span class="match-card-meaning-text">' + card.meaning + '</span>';
        }
        if (isMatched) {
            html += '<span class="match-card-check">✓</span>';
        }
        html += '</div>';
    });
    board.innerHTML = html;

    // 开始计时
    if (matchState.timerId) clearInterval(matchState.timerId);
    matchState.timer = 0;
    matchState.timerId = setInterval(function() {
        matchState.timer++;
        document.getElementById('matchTimer').textContent = matchState.timer;
    }, 1000);
}

function selectMatchCard(el) {
    // 已配对的不可选
    if (el.classList.contains('matched')) return;

    // 如果已选中两张，先清除
    var selectedCards = document.querySelectorAll('.match-card.selected');
    if (selectedCards.length >= 2) {
        selectedCards.forEach(function(c) { c.classList.remove('selected'); });
        matchState.selected = null;
    }

    el.classList.add('selected');

    selectedCards = document.querySelectorAll('.match-card.selected');
    if (selectedCards.length === 2) {
        checkMatch(selectedCards[0], selectedCards[1]);
    }
}

function checkMatch(card1, card2) {
    // 同一张卡不可配对
    if (card1.dataset.id === card2.dataset.id) {
        card2.classList.remove('selected');
        return;
    }

    // 同一类型不可配对
    if (card1.dataset.type === card2.dataset.type) {
        card2.classList.remove('selected');
        return;
    }

    var pairId = card1.dataset.pair;
    var isMatch = card2.dataset.pair === pairId;

    if (isMatch) {
        // 配对成功
        card1.classList.remove('selected');
        card2.classList.remove('selected');
        card1.classList.add('matched');
        card2.classList.add('matched');
        matchState.matched[pairId] = true;
        matchState.pairs++;

        // 添加 ✓ 标记
        card1.innerHTML = card1.innerHTML + '<span class="match-card-check">✓</span>';
        card2.innerHTML = card2.innerHTML + '<span class="match-card-check">✓</span>';

        document.getElementById('matchPairs').textContent = matchState.pairs;

        // 检查是否全部完成
        if (matchState.pairs >= L0_CHARS.length) {
            if (matchState.timerId) {
                clearInterval(matchState.timerId);
                matchState.timerId = null;
            }
            var resultEl = document.getElementById('matchResult');
            resultEl.classList.remove('hidden');
            resultEl.innerHTML = '<div class="match-result-win">🎉 恭喜完成！用时 ' + matchState.timer + ' 秒</div>' +
                '<button class="btn btn-retry" onclick="initMatch()">🔄 再来一次</button>';
        }
    } else {
        // 配对失败，取消选中
        setTimeout(function() {
            card1.classList.remove('selected');
            card2.classList.remove('selected');
        }, 500);
    }
}

function shuffleMatch() {
    initMatch();
}

// ==================== 工具函数 ====================
function shuffleArray(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var temp = a[i];
        a[i] = a[j];
        a[j] = temp;
    }
    return a;
}

function updateProgressBar() {
    var bar = document.getElementById('gameProgressBar');
    if (!bar) return;
    var progress = 0;
    if (currentMode === 'learn') {
        progress = 0;
    } else if (currentMode === 'quiz') {
        progress = Math.round((quizState.current / quizState.questions.length) * 100);
    } else if (currentMode === 'match') {
        progress = Math.round((matchState.pairs / L0_CHARS.length) * 100);
    }
    bar.style.width = progress + '%';
}