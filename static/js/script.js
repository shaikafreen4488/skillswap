document.addEventListener('DOMContentLoaded', function () {
  // 1. Bootstrap form validation messages
  document.querySelectorAll('.needs-validation').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });

  // 2. Ask before risky actions (forms with data-confirm="...")
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });

  // 3. Success and info messages fade away after a few seconds
  setTimeout(function () {
    document.querySelectorAll('.alert-success, .alert-info').forEach(function (alertBox) {
      var instance = window.bootstrap && bootstrap.Alert.getOrCreateInstance(alertBox);
      if (instance) { instance.close(); }
    });
  }, 6000);

  // 4. Password and confirm password must match
  var password = document.getElementById('password');
  var confirmPassword = document.getElementById('confirm_password');
  if (password && confirmPassword) {
    var check = function () {
      confirmPassword.setCustomValidity(confirmPassword.value && confirmPassword.value !== password.value ? 'No match' : '');
    };
    password.addEventListener('input', check);
    confirmPassword.addEventListener('input', check);
  }

  // 5. Fill the "Edit skill" window with the chosen skill
  var editModal = document.getElementById('editSkillModal');
  if (editModal) {
    editModal.addEventListener('show.bs.modal', function (event) {
      var button = event.relatedTarget;
      editModal.querySelector('form').action = button.dataset.action;
      editModal.querySelector('#edit-skill-name').textContent = button.dataset.name;
      editModal.querySelector('#edit-level').value = button.dataset.level;
      editModal.querySelector('#edit-description').value = button.dataset.description;
    });
  }

  // 6. Show a live character counter for text boxes with data-counter
  document.querySelectorAll('textarea[data-counter], input[data-counter]').forEach(function (field) {
    var counter = document.createElement('div');
    counter.className = 'form-text text-end';
    field.insertAdjacentElement('afterend', counter);
    var update = function () { counter.textContent = field.value.length + ' / ' + field.maxLength; };
    field.addEventListener('input', update);
    update();
  });
});
