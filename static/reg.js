document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('.create').addEventListener('click', function() {
        // Show the overlay
        document.getElementById('overlay').style.display = 'block';

        // Show and play the video
        var video = document.getElementById('loader');
        video.style.display = 'block';
        video.play();
    });
});