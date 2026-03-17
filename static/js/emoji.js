// ------------------------------------------------------------------
// Emoji Picker — standalone module
// Security note: emojis are plain Unicode characters, they pass
// through the existing innerHTML XSS channel unchanged.
// ------------------------------------------------------------------

var EMOJI_CATEGORIES = [
    {
        label: '顔',
        emojis: ['😀','😁','😂','🤣','😃','😄','😅','😆','😉','😊',
                 '😋','😎','😍','🥰','😘','😗','😙','😚','🙂','🤗',
                 '🤔','😐','😑','😶','🙄','😏','😣','😥','😮','🤐',
                 '😯','😪','😫','🥱','😴','😌','😛','😜','😝','🤤',
                 '😒','😓','😔','😕','🙃','🤑','😲','☹️','🙁','😖',
                 '😞','😟','😤','😢','😭','😦','😧','😨','😩','🤯',
                 '😬','😰','😱','🥵','🥶','😳','🤪','😵','😡','😠',
                 '🤬','😷','🤒','🤕','🤢','🤮','🤧','🥴','😇','🤠',
                 '🥸','🤡','🤥','🤫','🤭','🧐','🤓','😈','👿']
    },
    {
        label: 'ジェスチャー',
        emojis: ['👋','🤚','🖐️','✋','🖖','👌','🤌','🤏','✌️','🤞',
                 '🤟','🤘','🤙','👈','👉','👆','🖕','👇','☝️','👍',
                 '👎','✊','👊','🤛','🤜','👏','🙌','👐','🤲','🙏',
                 '✍️','💅','🤳','💪','🦾','🦿','🦵','🦶','👂','🦻',
                 '👃','🫀','🫁','🧠','🦷','🦴','👀','👁️','👅','👋']
    },
    {
        label: 'ハート',
        emojis: ['❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💔',
                 '❤️‍🔥','❤️‍🩹','❣️','💕','💞','💓','💗','💖','💘','💝',
                 '💟','☮️','✝️','☯️','🔴','🟠','🟡','🟢','🔵','🟣']
    },
    {
        label: '動物',
        emojis: ['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯',
                 '🦁','🐮','🐷','🐸','🐵','🙈','🙉','🙊','🐔','🐧',
                 '🐦','🐤','🦆','🦅','🦉','🦇','🐺','🐗','🐴','🦄',
                 '🐝','🪱','🐛','🦋','🐌','🐞','🐜','🪲','🦟','🦗',
                 '🪳','🕷️','🦂','🐢','🐍','🦎','🦖','🦕','🐙','🦑',
                 '🦐','🦞','🦀','🐡','🐠','🐟','🐬','🐳','🐋','🦈']
    },
    {
        label: '食べ物',
        emojis: ['🍎','🍐','🍊','🍋','🍌','🍉','🍇','🍓','🫐','🍈',
                 '🍒','🍑','🥭','🍍','🥥','🥝','🍅','🍆','🥑','🫒',
                 '🥦','🥬','🥒','🌶️','🫑','🧄','🧅','🥔','🍠','🫘',
                 '🌽','🍕','🌮','🌯','🫔','🥙','🧆','🥚','🍳','🥘',
                 '🍲','🫕','🥣','🥗','🍿','🧂','🥫','🍱','🍘','🍙',
                 '🍚','🍛','🍜','🍝','🍠','🍢','🍣','🍤','🍥','🥮',
                 '🍡','🧁','🍰','🎂','🍮','🍭','🍬','🍫','🍿','🍩',
                 '🍪','🌰','🥜','🍯','🧃','🥤','🧋','☕','🍵','🫖']
    },
    {
        label: 'その他',
        emojis: ['🔥','⭐','🌟','💫','✨','🎉','🎊','🎈','🎁','🏆',
                 '🥇','🥈','🥉','⚽','🏀','🏈','⚾','🎾','🏐','🏉',
                 '🎮','🕹️','🎯','🎲','🃏','🀄','🎪','🎭','🎨','🖼️',
                 '🎬','🎤','🎧','🎵','🎶','🎸','🎹','🎺','🥁','🪘',
                 '📱','💻','🖥️','⌨️','🖨️','🖱️','💾','💿','📷','📸',
                 '🔑','🗝️','🔒','🔓','🔨','⚒️','🛠️','⚙️','🔧','🔩',
                 '💡','🔦','🕯️','🪔','🧲','⚗️','🔭','🔬','🩺','💊',
                 '🌈','⛅','🌊','🌋','🏔️','🗺️','🌍','🌏','🌎','🚀']
    }
];

// Currently active category index
var emojiActiveCategory = 0;

// Reference to the open picker element (or null)
var emojiPickerEl = null;

// Reference to the textarea the picker is anchored to
var emojiTargetTextarea = null;

// ------------------------------------------------------------------
// Create and show the emoji picker
// ------------------------------------------------------------------
function showEmojiPicker(anchorBtn, textarea) {
    // Toggle — close if already open for the same button
    if (emojiPickerEl) {
        closeEmojiPicker();
        return;
    }

    emojiTargetTextarea = textarea;

    var picker = document.createElement('div');
    picker.className = 'emoji-picker';
    picker.setAttribute('role', 'dialog');
    picker.setAttribute('aria-label', '絵文字を選択');

    // Category tabs
    var tabBar = document.createElement('div');
    tabBar.className = 'emoji-category-tabs';

    EMOJI_CATEGORIES.forEach(function(cat, idx) {
        var tab = document.createElement('button');
        tab.className = 'emoji-category-tab' + (idx === emojiActiveCategory ? ' active' : '');
        tab.textContent = cat.label;
        tab.setAttribute('type', 'button');
        (function(i) {
            tab.onclick = function(e) {
                e.stopPropagation();
                emojiActiveCategory = i;
                renderEmojiGrid(picker, i);
                // Update tab active state
                picker.querySelectorAll('.emoji-category-tab').forEach(function(t, ti) {
                    t.classList.toggle('active', ti === i);
                });
            };
        })(idx);
        tabBar.appendChild(tab);
    });

    picker.appendChild(tabBar);

    // Grid container (will be populated by renderEmojiGrid)
    var gridContainer = document.createElement('div');
    gridContainer.className = 'emoji-grid-container';
    picker.appendChild(gridContainer);

    renderEmojiGrid(picker, emojiActiveCategory);

    // Position relative to the anchor button
    document.body.appendChild(picker);
    emojiPickerEl = picker;
    positionEmojiPicker(anchorBtn);

    // Close on outside click or ESC (next tick to avoid triggering on this click)
    setTimeout(function() {
        document.addEventListener('click', emojiOutsideClick, true);
        document.addEventListener('keydown', emojiEscHandler);
    }, 10);
}

function renderEmojiGrid(picker, catIdx) {
    var container = picker.querySelector('.emoji-grid-container');
    container.innerHTML = '';

    var grid = document.createElement('div');
    grid.className = 'emoji-grid';

    EMOJI_CATEGORIES[catIdx].emojis.forEach(function(emoji) {
        var item = document.createElement('button');
        item.className = 'emoji-item';
        item.textContent = emoji;
        item.setAttribute('type', 'button');
        item.setAttribute('aria-label', emoji);
        item.onclick = function(e) {
            e.stopPropagation();
            insertEmojiAtCursor(emoji);
        };
        grid.appendChild(item);
    });

    container.appendChild(grid);
}

function positionEmojiPicker(anchorBtn) {
    if (!emojiPickerEl) return;
    var rect = anchorBtn.getBoundingClientRect();
    var pickerHeight = 280;
    var pickerWidth = 320;

    // Prefer above anchor, fall back to below
    var top;
    if (rect.top > pickerHeight + 8) {
        top = rect.top - pickerHeight - 8;
    } else {
        top = rect.bottom + 8;
    }

    var left = Math.max(8, Math.min(rect.left, window.innerWidth - pickerWidth - 8));

    emojiPickerEl.style.top = top + 'px';
    emojiPickerEl.style.left = left + 'px';
}

function closeEmojiPicker() {
    if (emojiPickerEl) {
        emojiPickerEl.remove();
        emojiPickerEl = null;
    }
    document.removeEventListener('click', emojiOutsideClick, true);
    document.removeEventListener('keydown', emojiEscHandler);
}

function emojiOutsideClick(e) {
    if (emojiPickerEl && !emojiPickerEl.contains(e.target)) {
        closeEmojiPicker();
    }
}

function emojiEscHandler(e) {
    if (e.key === 'Escape') {
        closeEmojiPicker();
    }
}

// ------------------------------------------------------------------
// Insert emoji at cursor position in the target textarea
// ------------------------------------------------------------------
function insertEmojiAtCursor(emoji) {
    var ta = emojiTargetTextarea;
    if (!ta) return;

    var start = ta.selectionStart;
    var end = ta.selectionEnd;
    var value = ta.value;

    ta.value = value.slice(0, start) + emoji + value.slice(end);
    var newPos = start + emoji.length;
    ta.setSelectionRange(newPos, newPos);
    ta.focus();

    // Fire input event so char counter and draft save update
    ta.dispatchEvent(new Event('input', { bubbles: true }));

    // Keep picker open for multiple insertions
}
