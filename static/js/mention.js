// ------------------------------------------------------------------
// Feature 9: @mention autocomplete for compose and reply textareas
// ------------------------------------------------------------------

(function() {
    // Active dropdown reference
    var activeDropdown = null;
    var selectedIndex = -1;
    var dropdownItems = [];
    var activeTextarea = null;
    var mentionStart = -1;

    function closeMentionDropdown() {
        if (activeDropdown && activeDropdown.parentNode) {
            activeDropdown.parentNode.removeChild(activeDropdown);
        }
        activeDropdown = null;
        selectedIndex = -1;
        dropdownItems = [];
        mentionStart = -1;
    }

    function selectMentionItem(item, textarea) {
        var handle = item.dataset.handle; // e.g. "@alice"
        var val = textarea.value;
        var cursorPos = textarea.selectionStart;

        // Find the @ that started the mention
        var before = val.substring(0, cursorPos);
        var atIdx = before.lastIndexOf('@');
        if (atIdx < 0) { closeMentionDropdown(); return; }

        var newVal = val.substring(0, atIdx) + handle + ' ' + val.substring(cursorPos);
        textarea.value = newVal;

        var newCursor = atIdx + handle.length + 1;
        textarea.setSelectionRange(newCursor, newCursor);
        textarea.dispatchEvent(new Event('input'));
        closeMentionDropdown();
        textarea.focus();
    }

    function buildDropdown(users, textarea, rect, atIdx) {
        closeMentionDropdown();
        if (!users || users.length === 0) return;

        var dropdown = document.createElement('div');
        dropdown.className = 'mention-dropdown';
        dropdown.style.top = (rect.bottom + window.scrollY + 4) + 'px';
        dropdown.style.left = rect.left + 'px';

        selectedIndex = -1;
        dropdownItems = [];

        users.forEach(function(u, i) {
            var item = document.createElement('div');
            item.className = 'mention-item';
            item.dataset.handle = u.handle;

            var av = buildAvatar(u, 32);

            var info = document.createElement('div');
            info.className = 'mention-item-info';
            var name = document.createElement('div');
            name.className = 'mention-item-name';
            name.textContent = u.display_name;
            var handle = document.createElement('div');
            handle.className = 'mention-item-handle';
            handle.textContent = u.handle;
            info.appendChild(name);
            info.appendChild(handle);

            item.appendChild(av);
            item.appendChild(info);

            item.addEventListener('mousedown', function(e) {
                e.preventDefault();
                selectMentionItem(item, textarea);
            });

            dropdown.appendChild(item);
            dropdownItems.push(item);
        });

        document.body.appendChild(dropdown);
        activeDropdown = dropdown;
        activeTextarea = textarea;
    }

    function highlightItem(index) {
        dropdownItems.forEach(function(el, i) {
            el.classList.toggle('selected', i === index);
        });
    }

    // Attach mention autocomplete to a textarea
    function attachMentionAutocomplete(textarea) {
        var debounceTimer = null;

        textarea.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            var val = textarea.value;
            var cursor = textarea.selectionStart;
            var before = val.substring(0, cursor);

            // Find the last @ before the cursor that starts a word
            var match = before.match(/@([a-zA-Z0-9_]*)$/);
            if (!match) {
                closeMentionDropdown();
                return;
            }

            var prefix = match[1];
            mentionStart = before.lastIndexOf('@');

            if (prefix.length === 0) {
                closeMentionDropdown();
                return;
            }

            debounceTimer = setTimeout(function() {
                fetch('/api/users/search/mentions?q=' + encodeURIComponent(prefix))
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        var users = data.users || [];
                        var rect = textarea.getBoundingClientRect();
                        buildDropdown(users, textarea, rect, mentionStart);
                    })
                    .catch(function() { closeMentionDropdown(); });
            }, 200);
        });

        textarea.addEventListener('keydown', function(e) {
            if (!activeDropdown) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                closeMentionDropdown();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, dropdownItems.length - 1);
                highlightItem(selectedIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                highlightItem(selectedIndex);
            } else if ((e.key === 'Enter' || e.key === 'Tab') && selectedIndex >= 0) {
                e.preventDefault();
                selectMentionItem(dropdownItems[selectedIndex], textarea);
            }
        });

        textarea.addEventListener('blur', function() {
            // Small delay so mousedown events on items fire first
            setTimeout(function() {
                if (activeTextarea === textarea) closeMentionDropdown();
            }, 150);
        });
    }

    // Close dropdown on scroll or resize
    document.addEventListener('scroll', function() { closeMentionDropdown(); }, true);
    window.addEventListener('resize', function() { closeMentionDropdown(); });

    // Expose globally
    window.attachMentionAutocomplete = attachMentionAutocomplete;
})();
