(function() {
    'use strict';

    // Set client local date for timezone-accurate check-in
    var clientDateInput = document.getElementById('client_date');
    if (clientDateInput) {
        var now = new Date();
        var year = now.getFullYear();
        var month = String(now.getMonth() + 1).padStart(2, '0');
        var day = String(now.getDate()).padStart(2, '0');
        clientDateInput.value = year + '-' + month + '-' + day;
    }

    var csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    var REACTIONS = ['\u{1F44D}', '\u{1F525}', '\u{1F4AA}', '\u{1F389}', '\u{2764}\u{FE0F}', '\u{1F44F}'];

    var challengeView = document.querySelector('.challenge-view');
    var challengeId = challengeView ? challengeView.dataset.challengeId : null;

    if (!challengeId) return;

    // ===============================
    // BFCACHE + CHECKIN STATE
    // ===============================
    // Safari/iOS caches pages in bfcache. Force reload so server-rendered
    // state (checked-in vs not) is always fresh.
    window.addEventListener('pageshow', function(e) {
        if (e.persisted) {
            window.location.reload();
        }
    });

    // Also check localStorage for today's check-in (covers race conditions)
    var todayKey = 'checkin_' + challengeId + '_' + new Date().toISOString().slice(0, 10);
    var checkinForm = document.querySelector('.checkin-section form[action*="checkin"]');
    if (checkinForm && localStorage.getItem(todayKey)) {
        // Already checked in today — hide the form and show success state
        var card = checkinForm.closest('.checkin-card');
        if (card) {
            card.classList.add('checked');
            card.innerHTML =
                '<div class="checked-icon">\u2705</div>' +
                '<h2>You\'re all set for today!</h2>';
        }
    }

    // ===============================
    // CONFETTI
    // ===============================
    function launchConfetti() {
        var canvas = document.createElement('canvas');
        canvas.id = 'confetti-canvas';
        canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:9999';
        document.body.appendChild(canvas);

        var ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        var particles = [];
        var colors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];

        for (var i = 0; i < 120; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: canvas.height + Math.random() * 100,
                vx: (Math.random() - 0.5) * 8,
                vy: -(Math.random() * 16 + 8),
                color: colors[Math.floor(Math.random() * colors.length)],
                size: Math.random() * 8 + 4,
                rotation: Math.random() * 360,
                rotSpeed: (Math.random() - 0.5) * 10,
                gravity: 0.25 + Math.random() * 0.15,
                opacity: 1,
                shape: Math.random() > 0.5 ? 'rect' : 'circle'
            });
        }

        var frame = 0;
        var maxFrames = 150;

        function animate() {
            frame++;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            var alive = false;
            for (var i = 0; i < particles.length; i++) {
                var p = particles[i];
                p.vy += p.gravity;
                p.x += p.vx;
                p.y += p.vy;
                p.rotation += p.rotSpeed;
                if (frame > maxFrames * 0.6) {
                    p.opacity -= 0.02;
                }

                if (p.opacity <= 0) continue;
                alive = true;

                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate(p.rotation * Math.PI / 180);
                ctx.globalAlpha = Math.max(0, p.opacity);
                ctx.fillStyle = p.color;

                if (p.shape === 'rect') {
                    ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
                } else {
                    ctx.beginPath();
                    ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.restore();
            }

            if (alive && frame < maxFrames) {
                requestAnimationFrame(animate);
            } else {
                canvas.remove();
            }
        }
        requestAnimationFrame(animate);
    }

    // ===============================
    // AJAX CHECK-IN
    // ===============================
    if (checkinForm) {
        checkinForm.addEventListener('submit', function(e) {
            e.preventDefault();

            var submitBtn = checkinForm.querySelector('button[type="submit"]');
            var originalHTML = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<svg class="spinner" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10" opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10"/></svg> Checking in...';

            var formData = new FormData(checkinForm);

            fetch(checkinForm.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: formData
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalHTML;
                    if (window.SocialContract && window.SocialContract.flash) {
                        window.SocialContract.flash(data.error, 'error');
                    }
                    return;
                }

                // SUCCESS - Launch confetti!
                launchConfetti();

                // Mark today's check-in in localStorage
                var doneKey = 'checkin_' + challengeId + '_' + new Date().toISOString().slice(0, 10);
                try { localStorage.setItem(doneKey, '1'); } catch(e) {}

                // Replace the check-in card with the success state
                var checkinCard = document.querySelector('.checkin-card');
                var challengeName = challengeView.dataset.challengeName || 'a challenge';
                var joinCode = challengeView.dataset.joinCode || '';
                if (checkinCard) {
                    checkinCard.classList.add('checked');
                    var shareBtnHTML = '';
                    if (navigator.share) {
                        shareBtnHTML = '<button type="button" class="btn btn-ghost btn-sm share-streak-btn" id="share-streak-btn">' +
                            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
                            '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>' +
                            '<line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>' +
                            '</svg> Share Streak</button>';
                    }
                    checkinCard.innerHTML =
                        '<div class="checked-icon">\u2705</div>' +
                        '<h2>You\'re all set for today!</h2>' +
                        '<div class="checkin-success-details">' +
                            '<div class="success-stat">' +
                                '<span class="success-stat-value">+' + data.points_earned + '</span>' +
                                '<span class="success-stat-label">points earned</span>' +
                            '</div>' +
                            '<div class="success-stat">' +
                                '<span class="success-stat-value">\uD83D\uDD25 ' + data.new_streak + '</span>' +
                                '<span class="success-stat-label">day streak</span>' +
                            '</div>' +
                        '</div>' +
                        (data.freeze_used ? '<p class="freeze-notice">\u2744\uFE0F Streak freeze used to save your streak!</p>' : '') +
                        (data.freeze_earned > 0 ? '<p class="freeze-notice">\u2744\uFE0F +' + data.freeze_earned + ' streak freeze' + (data.freeze_earned > 1 ? 's' : '') + ' earned!</p>' : '') +
                        shareBtnHTML;

                    // Wire up the share button
                    var shareStreakBtn = document.getElementById('share-streak-btn');
                    if (shareStreakBtn) {
                        shareStreakBtn.addEventListener('click', function() {
                            var joinUrl = window.location.origin + '/challenge/join?code=' + joinCode;
                            navigator.share({
                                title: 'Streak Update!',
                                text: 'I just hit a ' + data.new_streak + '-day streak in "' + challengeName + '" on Social Contract! Join me:',
                                url: joinUrl
                            }).catch(function() {});
                        });
                    }
                }

                // Update the badge in the header
                var headerBadge = document.querySelector('.challenge-title-row .badge');
                if (headerBadge) {
                    headerBadge.className = 'badge badge-success badge-lg';
                    headerBadge.textContent = 'Checked in';
                } else {
                    var titleRow = document.querySelector('.challenge-title-row');
                    if (titleRow) {
                        var badge = document.createElement('span');
                        badge.className = 'badge badge-success badge-lg';
                        badge.textContent = 'Checked in';
                        titleRow.appendChild(badge);
                    }
                }

                // Show flash message
                if (window.SocialContract && window.SocialContract.flash) {
                    window.SocialContract.flash(data.message, 'success');
                }
            })
            .catch(function() {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHTML;
                if (window.SocialContract && window.SocialContract.flash) {
                    window.SocialContract.flash('Something went wrong. Please try again.', 'error');
                }
            });
        });
    }

    // ===============================
    // REACTIONS
    // ===============================
    document.querySelectorAll('.reaction-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            sendReaction(this.dataset.checkinId, this.dataset.reaction, this);
        });
    });

    document.querySelectorAll('.reaction-add').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var existing = document.querySelector('.reaction-picker');
            if (existing) { existing.remove(); return; }

            var picker = document.createElement('div');
            picker.className = 'reaction-picker';
            REACTIONS.forEach(function(emoji) {
                var opt = document.createElement('button');
                opt.type = 'button';
                opt.className = 'reaction-picker-opt';
                opt.textContent = emoji;
                opt.addEventListener('click', function() {
                    sendReaction(btn.dataset.checkinId, emoji);
                    picker.remove();
                });
                picker.appendChild(opt);
            });
            this.parentElement.appendChild(picker);

            setTimeout(function() {
                document.addEventListener('click', function close() {
                    picker.remove();
                    document.removeEventListener('click', close);
                });
            }, 0);
        });
    });

    // ===============================
    // NUDGE
    // ===============================
    document.querySelectorAll('.nudge-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var userId = this.dataset.userId;
            var btnEl = this;
            btnEl.disabled = true;
            btnEl.textContent = 'Sending...';

            fetch('/challenge/' + challengeId + '/nudge/' + userId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    btnEl.textContent = data.error;
                    setTimeout(function() {
                        btnEl.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg> Nudge';
                        btnEl.disabled = false;
                    }, 2000);
                } else {
                    btnEl.textContent = 'Nudged!';
                    btnEl.classList.add('nudged');
                }
            })
            .catch(function() {
                btnEl.textContent = 'Error';
                btnEl.disabled = false;
            });
        });
    });

    // ===============================
    // SEND REACTION
    // ===============================
    function sendReaction(checkinId, reaction, btnEl) {
        fetch('/challenge/' + challengeId + '/react', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ checkin_id: parseInt(checkinId), reaction: reaction })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) return;
            if (btnEl) {
                var countEl = btnEl.querySelector('.reaction-count');
                if (data.action === 'removed' && data.count === 0) {
                    btnEl.remove();
                } else {
                    countEl.textContent = data.count;
                    btnEl.classList.toggle('reacted', data.action === 'added');
                }
            } else {
                location.reload();
            }
        })
        .catch(function() {});
    }

    // ===============================
    // WEB SHARE API
    // ===============================
    var shareBtn = document.getElementById('share-native-btn');
    if (shareBtn && navigator.share) {
        // Show the button (hidden by default via CSS)
        var shareSection = shareBtn.closest('.share-section') || shareBtn.closest('.share-card');
        if (shareSection) shareSection.classList.add('has-share-api');
        shareBtn.style.display = 'inline-flex';

        shareBtn.addEventListener('click', function() {
            var title = this.dataset.shareTitle || 'Join my challenge';
            var code = this.dataset.shareCode || '';
            navigator.share({
                title: 'Join "' + title + '" on Social Contract',
                text: 'Join my "' + title + '" challenge! Use code: ' + code,
                url: window.location.href
            }).catch(function() {
                // User cancelled share — no action needed
            });
        });
    }

    // ===============================
    // LIVE COMMENT POLLING
    // ===============================
    var commentsSection = document.querySelector('.comments-list');
    if (commentsSection) {
        var lastCommentCount = commentsSection.querySelectorAll('.comment-item').length;

        setInterval(function() {
            fetch('/api/challenge/' + challengeId + '/leaderboard')
                .then(function(r) { return r.json(); })
                .then(function() {
                    // Lightweight poll - a full comment API would be better but this
                    // at least keeps the notification badge updated via script.js
                })
                .catch(function() {});
        }, 30000);
    }
})();
