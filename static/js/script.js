document.addEventListener("DOMContentLoaded", function () {
  // Flash message auto-hide
  const flashMessage = document.querySelector('.flash-messages');
  if (flashMessage) {
      setTimeout(() => {
          flashMessage.style.display = 'none';
      }, 5000); // Hide after 5 seconds
  }
  
  const toggleMenuButton = document.getElementById("toggle-menu");
  const sidebar = document.querySelector(".sidebar");

  toggleMenuButton.addEventListener("click", function () {
    sidebar.classList.toggle("active");
  });

  const editProfileBtn = document.getElementById("edit-profile-btn");
  const editProfileModal = document.getElementById("edit-profile-modal");
  const closeModal = document.getElementById("close-modal");

  // Ensure that the editProfileBtn exists to avoid errors
  if (editProfileBtn) {
    // Autofill modal with current user info when opened
    editProfileBtn.addEventListener("click", (e) => {
      e.preventDefault(); // Prevent the default anchor behavior

      // Read data-* attributes
      const username = editProfileBtn.dataset.username || "";
      const name = editProfileBtn.dataset.name || "";
      const email = editProfileBtn.dataset.email || "";
      const phone = editProfileBtn.dataset.phone || "";

      // Populate form fields
      document.getElementById("username").value = username;
      document.getElementById("name").value = name;
      document.getElementById("email").value = email;
      document.getElementById("phone").value = phone;

      editProfileModal.style.display = "block";
    });
  }

  // Close modal when the close button is clicked
  if (closeModal) {
    closeModal.addEventListener("click", () => {
      editProfileModal.style.display = "none";
    });
  }

  // Close modal when clicking outside the modal content
  window.addEventListener("click", (event) => {
    if (event.target === editProfileModal) {
      editProfileModal.style.display = "none";
    }
  });
});
