(function() {
    'use strict';

    var basePointsInput = document.getElementById('points_per_checkin');
    var streakBonusInput = document.getElementById('streak_bonus');
    var endDateInput = document.getElementById('end_date');

    if (!basePointsInput || !streakBonusInput || !endDateInput) return;

    // Set minimum date to tomorrow
    var tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    endDateInput.min = tomorrow.toISOString().split('T')[0];

    function updatePreview() {
        var base = parseInt(basePointsInput.value) || 10;
        var bonus = parseInt(streakBonusInput.value) || 5;

        var d1 = document.getElementById('day1-points');
        var d5 = document.getElementById('day5-points');
        var d7 = document.getElementById('day7-points');
        var d30 = document.getElementById('day30-points');

        if (d1) d1.textContent = base + ' pts';
        if (d5) d5.textContent = (base + bonus * 4) + ' pts';
        if (d7) d7.textContent = (base + bonus * 6) + ' pts';
        if (d30) d30.textContent = (base + bonus * 29) + ' pts';
    }

    basePointsInput.addEventListener('input', updatePreview);
    streakBonusInput.addEventListener('input', updatePreview);

    // Template confirmation modal
    var modal = document.getElementById('template-modal');
    var modalName = document.getElementById('modal-challenge-name');
    var modalDesc = document.getElementById('modal-challenge-desc');
    var modalDuration = document.getElementById('modal-challenge-duration');
    var modalPoints = document.getElementById('modal-challenge-points');
    var modalStreak = document.getElementById('modal-challenge-streak');
    var modalVerification = document.getElementById('modal-challenge-verification');
    var modalConfirm = document.getElementById('modal-confirm-btn');
    var modalCancel = document.getElementById('modal-cancel-btn');
    var modalCustomize = document.getElementById('modal-customize-btn');

    var selectedTemplateData = null;

    function showModal(data) {
        selectedTemplateData = data;
        if (modalName) modalName.textContent = data.name;
        if (modalDesc) modalDesc.textContent = data.description;
        if (modalDuration) modalDuration.textContent = data.duration + ' days';
        if (modalPoints) modalPoints.textContent = data.points + ' pts/day';
        if (modalStreak) modalStreak.textContent = '+' + data.streak + ' streak bonus';

        var verificationLabels = {
            'none': 'Tap only',
            'photo_optional': 'Photo optional',
            'photo_required': 'Photo required'
        };
        if (modalVerification) modalVerification.textContent = verificationLabels[data.verification] || data.verification;

        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    function hideModal() {
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
        selectedTemplateData = null;
    }

    function fillFormAndSubmit() {
        if (!selectedTemplateData) return;
        var d = selectedTemplateData;

        document.getElementById('name').value = d.name;
        document.getElementById('description').value = d.description;
        document.getElementById('points_per_checkin').value = d.points;
        document.getElementById('streak_bonus').value = d.streak;
        document.getElementById('verification_type').value = d.verification;

        var duration = parseInt(d.duration);
        if (duration) {
            var end = new Date();
            end.setDate(end.getDate() + duration);
            document.getElementById('end_date').value = end.toISOString().split('T')[0];
        }

        hideModal();

        // Submit the form directly
        var form = document.querySelector('form.form-card');
        if (form) form.submit();
    }

    function fillFormAndCustomize() {
        if (!selectedTemplateData) return;
        var d = selectedTemplateData;

        var nameInput = document.getElementById('name');
        nameInput.value = d.name;
        document.getElementById('description').value = d.description;
        document.getElementById('points_per_checkin').value = d.points;
        document.getElementById('streak_bonus').value = d.streak;
        document.getElementById('verification_type').value = d.verification;

        var duration = parseInt(d.duration);
        if (duration) {
            var end = new Date();
            end.setDate(end.getDate() + duration);
            document.getElementById('end_date').value = end.toISOString().split('T')[0];
        }

        updatePreview();
        hideModal();

        // Scroll to form so user can customize
        nameInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        nameInput.focus();
    }

    // Template card clicks
    document.querySelectorAll('.template-card').forEach(function(card) {
        card.addEventListener('click', function() {
            document.querySelectorAll('.template-card').forEach(function(c) {
                c.classList.remove('selected');
            });
            this.classList.add('selected');

            showModal({
                name: this.dataset.name,
                description: this.dataset.description,
                points: this.dataset.points,
                streak: this.dataset.streak,
                verification: this.dataset.verification,
                duration: this.dataset.duration
            });
        });
    });

    if (modalConfirm) modalConfirm.addEventListener('click', fillFormAndSubmit);
    if (modalCancel) modalCancel.addEventListener('click', hideModal);
    if (modalCustomize) modalCustomize.addEventListener('click', fillFormAndCustomize);

    // Close modal on backdrop click
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) hideModal();
        });
    }

    // Close modal on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && modal.classList.contains('active')) {
            hideModal();
        }
    });
})();
