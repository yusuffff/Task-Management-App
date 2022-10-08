'use strict';
// firebase.auth().signOut();
window.addEventListener('load', function () {

  if(document.getElementById('sign-out'))
    document.getElementById('sign-out').onclick = function () {
      firebase.auth().signOut();
      document.location.href = "/logout";
    };

  // FirebaseUI config.
  var uiConfig = {
    signInSuccessUrl: '/login',
    signInOptions: [
      firebase.auth.EmailAuthProvider.PROVIDER_ID,
    ],
  };

  firebase.auth().onAuthStateChanged(function (user) {
    if (user) {

      console.log(`Signed in as ${user.displayName} (${user.email})`);
      user.getIdToken().then(function (token) {
        document.cookie = "token=" + token + ";path=/";
      });
    } else {
      // User is signed out.
      // Initialize the FirebaseUI Widget using Firebase.
      var ui = new firebaseui.auth.AuthUI(firebase.auth());
      // Show the Firebase login button.
      ui.start('#firebaseui-auth-container', uiConfig);
      // Clear the token cookie.
      document.cookie = "token=;path=/"
    }
  }, function (error) {
    console.log(error);
    alert('Unable to log in: ' + error)
  });
});



$(document).ready(function () {
    $("#boarddetailspage").click(function () {
        $('#boardidfortask').val($(this).data('id'));
    });

    $("#inviteusermodal").click(function () {
        $('#boardidforuser').val($(this).data('id'));
    });

    $(".edittaskitem").click(function () {
      $("#edittasktitle").val($(this).data('name'))
      $("#edittaskduedate").val($(this).data('date'))
      $("#edittaskasignto").val($(this).data('assign'))
      $("#edittaskid").val($(this).data('id'))
    })

    $(".renameboard").click(function () {
      $("#renameboard").val($(this).data('name'))
      $("#board_id").val($(this).data('id'))
    })

    $("#removeuserfrommodal").click(function () {
      $("#removeuserfrommodal_board_id").val($(this).data('id'))
    })



});
