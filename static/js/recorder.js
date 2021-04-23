let audio_blob = null;
let selectedMedia = "aud";

// This array stores the recorded media data
let chunks = [];


const audioMediaConstraints = {
	audio: true,
	video: false,
};

const videoMediaConstraints = {

	audio: true,
	video: true,
};


function startRecording(
	thisButton, otherButton) {
	var user_name = $("#user-name").val();
	if(user_name == ""){
		$(".name-alert").show();
	}
	else{
		$(".name-alert").hide();
		$(".success-alert").hide();
		$(".error-alert").hide();

		// Access the camera and microphone
	$("#recording").remove();
	$("#recording-link").remove();
	navigator.mediaDevices.getUserMedia(
		selectedMedia === "vid" ?
		videoMediaConstraints :
		audioMediaConstraints)
		.then((mediaStream) => {

		// Create a new MediaRecorder instance
		const mediaRecorder =
			new MediaRecorder(mediaStream);

		//Make the mediaStream global
		window.mediaStream = mediaStream;
		//Make the mediaRecorder global
		window.mediaRecorder = mediaRecorder;

		mediaRecorder.start();
		
		mediaRecorder.ondataavailable = (e) => {

			chunks.push(e.data);
		};

		mediaRecorder.onstop = () => {

			const blob = new Blob(
				chunks, {
					type: selectedMedia === "vid" ?
						"video/mp4" : "audio/wav"
				});
			chunks = [];

			const recordedMedia = document.createElement(
				selectedMedia === "vid" ? "video" : "audio");
			recordedMedia.controls = true;
			recordedMedia.id = 'recording';
			audio_blob = blob;
			const recordedMediaURL = URL.createObjectURL(blob);

			recordedMedia.src = recordedMediaURL;
			
			$(".upload-btn").show();


			document.getElementById(
				`${selectedMedia}-recorder`).append(
				recordedMedia);
		};

		document.getElementById(
				`${selectedMedia}-record-status`)
				.innerText = "Recording";

		thisButton.disabled = true;
		otherButton.disabled = false;
	});
	}
}

function stopRecording(thisButton, otherButton) {

	// Stop the recording
	window.mediaRecorder.stop();

	// Stop all the tracks in the
	// received media stream
	window.mediaStream.getTracks()
	.forEach((track) => {
		track.stop();
	});

	document.getElementById(
			`${selectedMedia}-record-status`)
			.innerText = "Recording done!";
	thisButton.disabled = true;
	otherButton.disabled = false;
}

$('.upload-btn').click(function(e) {
	var formData = new FormData();
	$(".wait-alert").show();
	$(".error-alert").hide();
	var user_name = $("#user-name").val();
	var d = new Date();
	var datestring = ("0" + d.getDate()).slice(-2) + "-" + ("0"+(d.getMonth()+1)).slice(-2) + "-" +
	d.getFullYear() + "-" + ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
	var file_name = user_name+"-"+datestring+".wav";
	
	var reader = new FileReader();
	var base64data;
	reader.readAsDataURL(audio_blob); 
	reader.onloadend = function() {
		
		base64data = reader.result;    
		formData.append("recording", base64data);
		formData.append("file_name", file_name);

		$.ajax({
				url: "/upload",
				type: 'POST',
				contentType: false,
				processData: false,
				data: formData,
				success: function (data,status,xhr) {
					if(xhr.status==200) {
						$("#recording").remove();
						$(".wait-alert").hide();
						$(".success-alert").html($(".success-alert").html().trim()+", "+user_name.charAt(0).toUpperCase() +
						user_name.slice(1));
						$(".success-alert").show();
						$(".upload-btn").hide();
						$("#user-name").val("");
						audio_blob = null;
					}
				},
				error: function(data, textStatus, errorThrown) {
					console.log(data,textStatus, errorThrown);
					$(".error-alert").show();
					$(".wait-alert").hide();
				}
			});

	}
});
