/**
 * Social Contract
 * Premium, performant JavaScript
 */

(function() {
    'use strict';

    // ============================================
    // CONFIG
    // ============================================
    
    const CONFIG = {
        animationDuration: 300,
        flashDismissDelay: 5000,
        debounceDelay: 150,
        observerThreshold: 0.15,
    };

    // ============================================
    // UTILITIES
    // ============================================
    
    const $ = (sel, ctx = document) => ctx.querySelector(sel);
    const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
    
    const prefersReducedMotion = () => 
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const debounce = (fn, delay = CONFIG.debounceDelay) => {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    };

    // ============================================
    // FLASH MESSAGES
    // ============================================
    
    const FlashMessages = {
        init() {
            $$('.flash').forEach(flash => this.setup(flash));
        },

        setup(flash) {
            const timeout = setTimeout(() => this.dismiss(flash), CONFIG.flashDismissDelay);
            
            const close = $('.flash-close', flash);
            if (close) {
                close.addEventListener('click', () => {
                    clearTimeout(timeout);
                    this.dismiss(flash);
                });
            }
            
            flash.addEventListener('mouseenter', () => clearTimeout(timeout));
            flash.addEventListener('mouseleave', () => {
                setTimeout(() => this.dismiss(flash), 2000);
            });
        },

        dismiss(flash) {
            if (prefersReducedMotion()) {
                flash.remove();
                return;
            }
            
            flash.style.opacity = '0';
            flash.style.transform = 'translateX(20px)';
            setTimeout(() => flash.remove(), CONFIG.animationDuration);
        },

        show(message, type = 'success') {
            let container = $('.flash-messages');
            if (!container) {
                container = document.createElement('div');
                container.className = 'flash-messages';
                document.body.appendChild(container);
            }

            const icons = {
                success: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
                error: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`
            };

            const flash = document.createElement('div');
            flash.className = `flash flash-${type}`;
            flash.innerHTML = `
                <span>${icons[type] || icons.success}</span>
                <span>${message}</span>
                <button class="flash-close" aria-label="Dismiss">×</button>
            `;
            
            container.appendChild(flash);
            this.setup(flash);
        }
    };

    // ============================================
    // FORMS
    // ============================================
    
    const Forms = {
        init() {
            $$('form').forEach(form => this.setup(form));
        },

        setup(form) {
            form.addEventListener('submit', e => this.handleSubmit(e, form));
            
            $$('input, textarea', form).forEach(input => {
                input.addEventListener('blur', () => this.validate(input));
                input.addEventListener('input', debounce(() => {
                    if (input.checkValidity()) {
                        input.classList.remove('is-invalid');
                    }
                }));
            });
        },

        handleSubmit(e, form) {
            const btn = $('button[type="submit"]', form);
            if (!btn || btn.disabled) return;
            
            const inputs = $$('input[required], textarea[required]', form);
            let valid = true;
            
            inputs.forEach(input => {
                if (!this.validate(input)) valid = false;
            });

            if (!valid) {
                e.preventDefault();
                return;
            }

            this.setLoading(btn, true);
        },

        validate(input) {
            if (!input.required) return true;
            
            const valid = input.checkValidity();
            input.classList.toggle('is-invalid', !valid);
            return valid;
        },

        setLoading(btn, loading) {
            if (loading) {
                btn.disabled = true;
                btn.classList.add('is-loading');
                btn.setAttribute('aria-busy', 'true');
                btn.dataset.text = btn.innerHTML;
                btn.innerHTML = `
                    <svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <circle cx="12" cy="12" r="10" opacity="0.25"/>
                        <path d="M12 2a10 10 0 0 1 10 10"/>
                    </svg>
                    <span>Loading...</span>
                `;
            } else {
                btn.disabled = false;
                btn.classList.remove('is-loading');
                btn.setAttribute('aria-busy', 'false');
                btn.innerHTML = btn.dataset.text || 'Submit';
            }
        }
    };

    // ============================================
    // ANIMATIONS
    // ============================================
    
    const Animations = {
        init() {
            if (prefersReducedMotion()) return;
            
            this.setupScrollReveal();
            this.setupHeroAnimations();
        },

        setupScrollReveal() {
            const targets = $$('.stat-card, .challenge-card, .l-step');
            if (!targets.length) return;

            targets.forEach((el, i) => {
                el.style.opacity = '0';
                el.style.transform = 'translateY(20px)';
                el.style.transition = `opacity 0.5s ease ${i * 0.06}s, transform 0.5s ease ${i * 0.06}s`;
            });

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: CONFIG.observerThreshold });

            targets.forEach(el => observer.observe(el));
        },

        setupHeroAnimations() {
            const hero = $('.l-hero');
            if (!hero) return;

            const content = $('.l-hero-content', hero);
            const visual = $('.l-hero-visual', hero);

            if (content) {
                content.style.opacity = '0';
                content.style.transform = 'translateY(30px)';
                requestAnimationFrame(() => {
                    content.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
                    content.style.opacity = '1';
                    content.style.transform = 'translateY(0)';
                });
            }

            if (visual) {
                visual.style.opacity = '0';
                visual.style.transform = 'translateY(40px)';
                requestAnimationFrame(() => {
                    visual.style.transition = 'opacity 0.8s ease 0.2s, transform 0.8s ease 0.2s';
                    visual.style.opacity = '1';
                    visual.style.transform = 'translateY(0)';
                });
            }
        }
    };

    // ============================================
    // KEYBOARD SHORTCUTS
    // ============================================
    
    const Keyboard = {
        init() {
            document.addEventListener('keydown', e => this.handle(e));
        },

        handle(e) {
            // Ignore if in input
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
            
            // Escape closes modals/dropdowns
            if (e.key === 'Escape') {
                $$('.flash').forEach(f => FlashMessages.dismiss(f));
            }
            
            // Slash focuses search if present
            if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
                const search = $('input[type="search"], input[name="search"]');
                if (search) {
                    e.preventDefault();
                    search.focus();
                }
            }
        }
    };

    // ============================================
    // CLIPBOARD
    // ============================================
    
    const Clipboard = {
        init() {
            $$('[data-copy]').forEach(btn => {
                btn.addEventListener('click', () => this.copy(btn));
            });
        },

        async copy(btn) {
            const text = btn.dataset.copy;
            
            try {
                await navigator.clipboard.writeText(text);
                this.feedback(btn, true);
            } catch {
                // Fallback
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.cssText = 'position:fixed;opacity:0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                textarea.remove();
                this.feedback(btn, true);
            }
        },

        feedback(btn, success) {
            const original = btn.innerHTML;
            const originalTitle = btn.title;
            
            btn.innerHTML = success 
                ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`
                : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
            btn.title = success ? 'Copied!' : 'Failed';
            btn.classList.add('copied');
            
            setTimeout(() => {
                btn.innerHTML = original;
                btn.title = originalTitle;
                btn.classList.remove('copied');
            }, 2000);
        }
    };

    // ============================================
    // SMOOTH SCROLL
    // ============================================
    
    const SmoothScroll = {
        init() {
            $$('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', e => this.handle(e, anchor));
            });
        },

        handle(e, anchor) {
            const href = anchor.getAttribute('href');
            if (href === '#') return;

            const target = $(href);
            if (!target) return;

            e.preventDefault();
            
            target.scrollIntoView({
                behavior: prefersReducedMotion() ? 'auto' : 'smooth',
                block: 'start'
            });

            history.pushState(null, '', href);
        }
    };

    // ============================================
    // ACCESSIBILITY
    // ============================================
    
    const A11y = {
        init() {
            this.setupFocusVisible();
            this.createLiveRegion();
        },

        setupFocusVisible() {
            let hadKeyboard = false;
            
            document.addEventListener('keydown', () => hadKeyboard = true);
            document.addEventListener('mousedown', () => hadKeyboard = false);
            
            document.addEventListener('focusin', e => {
                if (hadKeyboard) e.target.classList.add('focus-visible');
            });
            
            document.addEventListener('focusout', e => {
                e.target.classList.remove('focus-visible');
            });
        },

        createLiveRegion() {
            if ($('#aria-live')) return;
            
            const region = document.createElement('div');
            region.id = 'aria-live';
            region.setAttribute('aria-live', 'polite');
            region.setAttribute('aria-atomic', 'true');
            region.className = 'sr-only';
            document.body.appendChild(region);
        },

        announce(message) {
            const region = $('#aria-live');
            if (region) {
                region.textContent = '';
                setTimeout(() => region.textContent = message, 100);
            }
        }
    };

    // ============================================
    // NUMBER COUNTER
    // ============================================
    
    const Counter = {
        init() {
            if (prefersReducedMotion()) return;
            
            const numbers = $$('[data-count]');
            if (!numbers.length) return;

            const observer = new IntersectionObserver(entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.animate(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.5 });

            numbers.forEach(el => observer.observe(el));
        },

        animate(el) {
            const target = parseInt(el.dataset.count, 10);
            const duration = 800;
            const start = performance.now();

            const step = (now) => {
                const progress = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                el.textContent = Math.floor(eased * target).toLocaleString();
                
                if (progress < 1) {
                    requestAnimationFrame(step);
                } else {
                    el.textContent = target.toLocaleString();
                }
            };

            requestAnimationFrame(step);
        }
    };

    // ============================================
    // MOBILE MENU
    // ============================================

    const MobileMenu = {
        init() {
            const btn = $('#mobile-menu-btn');
            const links = $('#nav-links');
            if (!btn || !links) return;

            btn.addEventListener('click', () => {
                links.classList.toggle('open');
                const isOpen = links.classList.contains('open');
                btn.setAttribute('aria-expanded', isOpen);
            });

            // Close menu when clicking a link
            $$('.nav-link', links).forEach(link => {
                link.addEventListener('click', () => {
                    links.classList.remove('open');
                });
            });

            // Close menu when clicking outside
            document.addEventListener('click', (e) => {
                if (!btn.contains(e.target) && !links.contains(e.target)) {
                    links.classList.remove('open');
                }
            });
        }
    };

    // ============================================
    // NOTIFICATIONS BADGE
    // ============================================

    const NotifBadge = {
        init() {
            const badge = $('#notif-badge');
            if (!badge) return;

            this.badge = badge;
            this.tabBadge = $('#tab-notif-badge');
            this.poll();
            setInterval(() => this.poll(), 30000);
        },

        async poll() {
            if (document.hidden) return; // Don't poll when tab is hidden
            try {
                const resp = await fetch('/api/notifications/unread-count');
                if (!resp.ok) return;
                const data = await resp.json();
                const count = data.count || 0;

                if (count > 0) {
                    const display = count > 99 ? '99+' : count;
                    this.badge.textContent = display;
                    this.badge.style.display = 'flex';
                    if (this.tabBadge) {
                        this.tabBadge.textContent = display;
                        this.tabBadge.style.display = 'flex';
                    }
                } else {
                    this.badge.style.display = 'none';
                    if (this.tabBadge) this.tabBadge.style.display = 'none';
                }
            } catch {
                // Silent fail for notification polling
            }
        }
    };

    // ============================================
    // QUICK CHECK-IN (Dashboard)
    // ============================================

    const QuickCheckin = {
        init() {
            const quickForms = $$('.quick-checkin-form');
            const cardForms = $$('.checkin-form');
            const forms = [...quickForms, ...cardForms];
            if (!forms.length) return;

            const csrfMeta = $('meta[name="csrf-token"]');
            const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

            forms.forEach(form => {
                form.addEventListener('click', e => e.stopPropagation());
                form.addEventListener('submit', e => {
                    e.preventDefault();
                    this.submit(form, csrfToken);
                });
            });
        },

        submit(form, csrfToken) {
            const btn = $('button[type="submit"]', form);
            if (!btn || btn.disabled) return;

            const originalHTML = btn.innerHTML;
            btn.disabled = true;
            btn.classList.add('is-loading');
            btn.setAttribute('aria-busy', 'true');
            btn.innerHTML = '<svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10" opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>';

            const formData = new FormData(form);
            const challengeId = this.getChallengeId(form);

            fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: formData
            })
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    btn.disabled = false;
                    btn.classList.remove('is-loading');
                    btn.setAttribute('aria-busy', 'false');
                    btn.innerHTML = originalHTML;
                    FlashMessages.show(data.error, 'error');
                    return;
                }

                // Haptic feedback
                if (navigator.vibrate) navigator.vibrate(50);

                this.markPendingListDone(challengeId, data.points_earned);
                this.markChallengeCardDone(challengeId);

                // Update progress bar
                this.updateProgress();

                FlashMessages.show(data.message || 'Checked in!', 'success');
            })
            .catch(() => {
                btn.disabled = false;
                btn.classList.remove('is-loading');
                btn.setAttribute('aria-busy', 'false');
                btn.innerHTML = originalHTML;
                FlashMessages.show('Something went wrong. Please try again.', 'error');
            });
        },

        getChallengeId(form) {
            const explicit = form.dataset.challengeId;
            if (explicit) return explicit;

            const item = form.closest('.today-pending-item');
            if (item && item.dataset.challengeId) return item.dataset.challengeId;

            const match = (form.action || '').match(/\/challenge\/(\d+)\/checkin/);
            return match ? match[1] : null;
        },

        markPendingListDone(challengeId, pointsEarned) {
            if (!challengeId) return;
            const item = $('#today-item-' + challengeId) || $('.today-pending-item[data-challenge-id="' + challengeId + '"]');
            if (!item || !item.classList.contains('today-pending-item')) return;

            const nameEl = $('.today-pending-name', item);
            const name = nameEl ? nameEl.textContent : 'Challenge';
            item.classList.add('checkin-success-flash');
            item.className = 'today-done-item checkin-success-flash';
            item.id = 'today-item-' + challengeId;
            item.innerHTML = '<span>\u2705</span><span class="today-pending-name">' +
                name +
                '</span><span class="today-pending-meta">+' + (pointsEarned || 0) + ' pts</span>';
        },

        markChallengeCardDone(challengeId) {
            if (!challengeId) return;
            const card = $$('.challenge-card').find(el => (el.getAttribute('href') || '').includes('/challenge/' + challengeId));
            if (!card) return;

            card.classList.add('checked-in');
            const badge = $('.badge', card);
            if (badge) {
                badge.className = 'badge badge-success';
                badge.textContent = 'Done';
            }
            const checkinForm = $('.checkin-form', card);
            if (checkinForm) checkinForm.remove();
        },

        updateProgress() {
            const allItems = $$('#today-pending-list > div');
            const doneItems = $$('#today-pending-list .today-done-item');
            const total = allItems.length;
            const done = doneItems.length;

            const countEl = $('#today-progress-count');
            if (countEl) countEl.textContent = done + '/' + total + ' done';

            const fillEl = $('#today-progress-fill');
            if (fillEl) fillEl.style.width = (total > 0 ? (done / total * 100) : 0) + '%';

            // All done state
            if (done >= total && total > 0) {
                const list = $('#today-pending-list');
                if (list) {
                    list.innerHTML = '<div class="today-all-done"><div class="today-all-done-icon">\uD83C\uDF89</div><h3>All done for today!</h3><p>You\'ve checked in to all your challenges. See you tomorrow!</p></div>';
                }
                if (navigator.vibrate) navigator.vibrate([50, 100, 50]);
            }
        }
    };

    // ============================================
    // PULL TO REFRESH
    // ============================================

    const PullToRefresh = {
        init() {
            // Only activate in PWA standalone mode
            if (!window.matchMedia('(display-mode: standalone)').matches &&
                !window.navigator.standalone) return;

            const main = $('.main-content');
            if (!main) return;

            this.startY = 0;
            this.pulling = false;
            this.indicator = null;

            main.addEventListener('touchstart', e => this.onTouchStart(e), { passive: true });
            main.addEventListener('touchmove', e => this.onTouchMove(e), { passive: false });
            main.addEventListener('touchend', e => this.onTouchEnd(e), { passive: true });
        },

        createIndicator() {
            if (this.indicator) return;
            const el = document.createElement('div');
            el.className = 'pull-to-refresh-indicator';
            el.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>';
            document.body.appendChild(el);
            this.indicator = el;
        },

        onTouchStart(e) {
            if (window.scrollY > 5) return;
            this.startY = e.touches[0].clientY;
            this.pulling = true;
        },

        onTouchMove(e) {
            if (!this.pulling || window.scrollY > 5) {
                this.pulling = false;
                return;
            }

            const dy = e.touches[0].clientY - this.startY;
            if (dy > 10) {
                this.createIndicator();
                if (this.indicator) {
                    const progress = Math.min(dy / 100, 1);
                    this.indicator.style.transform = 'translateX(-50%) translateY(' + (progress * 50 - 40) + 'px)';
                    this.indicator.classList.toggle('pulling', dy > 60);
                }
                if (dy > 30) e.preventDefault();
            }
        },

        onTouchEnd() {
            if (!this.pulling) return;
            this.pulling = false;

            if (this.indicator && this.indicator.classList.contains('pulling')) {
                this.indicator.classList.add('refreshing');
                this.indicator.style.transform = 'translateX(-50%) translateY(16px)';
                setTimeout(() => window.location.reload(), 300);
            } else if (this.indicator) {
                this.indicator.style.transform = 'translateX(-50%) translateY(-100%)';
                setTimeout(() => { if (this.indicator) this.indicator.remove(); this.indicator = null; }, 200);
            }
        }
    };

    // ============================================
    // EXPLORE FILTER & SORT
    // ============================================

    const ExploreFilter = {
        init() {
            const search = $('#explore-search');
            const sort = $('#explore-sort');
            const grid = $('.explore-grid');
            if (!search || !grid) return;

            this.grid = grid;
            this.cards = $$('.explore-card', grid);

            search.addEventListener('input', debounce(() => this.filter(search.value), 200));
            if (sort) sort.addEventListener('change', () => this.sort(sort.value));
        },

        filter(query) {
            const q = query.toLowerCase().trim();
            this.cards.forEach(card => {
                const name = (card.dataset.name || '').toLowerCase();
                const desc = (card.dataset.desc || '').toLowerCase();
                const match = !q || name.includes(q) || desc.includes(q);
                card.classList.toggle('explore-card-hidden', !match);
            });
        },

        sort(by) {
            const cards = [...this.cards].filter(c => !c.classList.contains('explore-card-hidden'));
            cards.sort((a, b) => {
                if (by === 'popular') return (parseInt(b.dataset.members) || 0) - (parseInt(a.dataset.members) || 0);
                if (by === 'alpha') return (a.dataset.name || '').localeCompare(b.dataset.name || '');
                return 0; // newest = default server order
            });
            cards.forEach(card => this.grid.appendChild(card));
        }
    };

    // ============================================
    // INIT
    // ============================================

    function init() {
        FlashMessages.init();
        Forms.init();
        Keyboard.init();
        SmoothScroll.init();
        Clipboard.init();
        A11y.init();
        Animations.init();
        Counter.init();
        MobileMenu.init();
        NotifBadge.init();
        QuickCheckin.init();
        PullToRefresh.init();
        ExploreFilter.init();

        // Dev log
        if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
            console.log('%c\uD83D\uDCDC Social Contract', 'font-size: 14px; font-weight: bold; color: #10b981;');
            console.log('%cReady', 'font-size: 11px; color: #71717a;');
        }
    }

    // Run
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Profile photo upload auto-submit
    const photoUpload = document.getElementById('photo-upload');
    if (photoUpload) {
        photoUpload.addEventListener('change', function() {
            const form = document.getElementById('photo-upload-form');
            if (form && this.files.length > 0) {
                form.submit();
            }
        });
    }

    // Stop propagation on checkin forms inside clickable cards
    $$('.checkin-form').forEach(form => {
        form.addEventListener('click', e => e.stopPropagation());
    });

    // Set client date fields for timezone-accurate check-ins
    $$('.client-date-field').forEach(input => {
        const now = new Date();
        const y = now.getFullYear();
        const m = String(now.getMonth() + 1).padStart(2, '0');
        const d = String(now.getDate()).padStart(2, '0');
        input.value = y + '-' + m + '-' + d;
    });

    // Auto-detect and set user timezone on all forms
    try {
        const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (userTz) {
            $$('.timezone-field').forEach(input => { input.value = userTz; });
        }
    } catch (e) {
        // Fallback: timezone fields already default to 'UTC'
    }

    // ============================================
    // SERVICE WORKER REGISTRATION
    // ============================================

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js', { scope: '/' })
            .then(function(reg) {
                // Check for updates periodically
                setInterval(function() { reg.update(); }, 60 * 60 * 1000); // hourly

                reg.addEventListener('updatefound', function() {
                    var newWorker = reg.installing;
                    if (newWorker) {
                        newWorker.addEventListener('statechange', function() {
                            if (newWorker.state === 'activated' && navigator.serviceWorker.controller) {
                                // New version available
                                FlashMessages.show('App updated! Refresh for the latest version.', 'success');
                            }
                        });
                    }
                });
            })
            .catch(function(err) {
                // SW registration failed — app still works normally
            });
    }

    // ============================================
    // PWA INSTALL PROMPT
    // ============================================

    const PWAInstall = {
        deferredPrompt: null,

        init() {
            // Don't show if already in standalone mode
            if (window.matchMedia('(display-mode: standalone)').matches) return;
            if (window.navigator.standalone) return;

            // Don't show if user dismissed recently
            if (localStorage.getItem('pwa-install-dismissed')) {
                const dismissed = parseInt(localStorage.getItem('pwa-install-dismissed'), 10);
                if (Date.now() - dismissed < 7 * 24 * 60 * 60 * 1000) return; // 7 days
            }

            // iOS detection
            const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
            if (isIOS) {
                setTimeout(() => this.showIOSBanner(), 3000);
                return;
            }

            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                this.deferredPrompt = e;
                setTimeout(() => this.showBanner(), 3000);
            });
        },

        showBanner() {
            if (!this.deferredPrompt) return;

            const banner = document.createElement('div');
            banner.className = 'pwa-install-banner';
            banner.innerHTML =
                '<div class="pwa-install-banner-icon">\u2694\uFE0F</div>' +
                '<div class="pwa-install-banner-text">' +
                    '<div class="pwa-install-banner-title">Install Social Contract</div>' +
                    '<div class="pwa-install-banner-desc">Add to home screen for the best experience</div>' +
                '</div>' +
                '<button class="pwa-install-btn">Install</button>' +
                '<button class="pwa-install-dismiss">\u00D7</button>';

            document.body.appendChild(banner);

            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    banner.classList.add('visible');
                });
            });

            banner.querySelector('.pwa-install-btn').addEventListener('click', () => {
                this.deferredPrompt.prompt();
                this.deferredPrompt.userChoice.then(() => {
                    this.deferredPrompt = null;
                    banner.classList.remove('visible');
                    setTimeout(() => banner.remove(), 300);
                });
            });

            banner.querySelector('.pwa-install-dismiss').addEventListener('click', () => {
                localStorage.setItem('pwa-install-dismissed', Date.now().toString());
                banner.classList.remove('visible');
                setTimeout(() => banner.remove(), 300);
            });
        },

        showIOSBanner() {
            const banner = document.createElement('div');
            banner.className = 'pwa-install-banner';
            banner.innerHTML =
                '<div class="pwa-install-banner-icon">\u2694\uFE0F</div>' +
                '<div class="pwa-install-banner-text">' +
                    '<div class="pwa-install-banner-title">Install Social Contract</div>' +
                    '<div class="pwa-ios-steps">' +
                        '<div class="pwa-ios-step"><span class="pwa-ios-step-num">1</span> Tap the <strong>Share</strong> button <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg></div>' +
                        '<div class="pwa-ios-step"><span class="pwa-ios-step-num">2</span> Tap <strong>Add to Home Screen</strong></div>' +
                    '</div>' +
                '</div>' +
                '<button class="pwa-install-dismiss">\u00D7</button>';

            document.body.appendChild(banner);

            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    banner.classList.add('visible');
                });
            });

            banner.querySelector('.pwa-install-dismiss').addEventListener('click', () => {
                localStorage.setItem('pwa-install-dismissed', Date.now().toString());
                banner.classList.remove('visible');
                setTimeout(() => banner.remove(), 300);
            });
        }
    };

    PWAInstall.init();

    // Public API
    window.SocialContract = {
        flash: FlashMessages.show.bind(FlashMessages),
        announce: A11y.announce.bind(A11y)
    };

})();
