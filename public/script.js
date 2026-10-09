const imageInput = document.getElementById("imageInput");
const preview = document.getElementById("preview");
const analyzeBtn = document.getElementById("analyzeBtn");
const resultBox = document.getElementById("result");

let selectedFile = null;
let previewURL = null;

if (!imageInput || !preview || !analyzeBtn || !resultBox) {
    console.error(
        "HTML elements missing. Check the IDs in index.html."
    );
} else {

    function updateButton() {
        analyzeBtn.disabled = !selectedFile;
    }

    imageInput.addEventListener("change", function () {
        const file = imageInput.files[0];

        selectedFile = null;
        updateButton();

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
            previewURL = null;
        }

        preview.removeAttribute("src");
        preview.hidden = true;

        if (!file) {
            resultBox.textContent = "Please select an image.";
            return;
        }

        const allowedTypes = [
            "image/jpeg",
            "image/png",
            "image/webp"
        ];

        if (!allowedTypes.includes(file.type)) {
            imageInput.value = "";

            resultBox.textContent =
                "Please select a JPG, PNG, or WEBP image.";

            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            imageInput.value = "";

            resultBox.textContent =
                "Image size must be less than 10 MB.";

            return;
        }

        selectedFile = file;

        previewURL = URL.createObjectURL(file);
        preview.src = previewURL;
        preview.hidden = false;

        resultBox.textContent =
            "Image selected! Click Analyze Image to continue.";

        updateButton();
    });


    analyzeBtn.addEventListener("click", async function () {

        if (!selectedFile) {
            resultBox.textContent =
                "Please select an image first.";
            return;
        }

        const fileToAnalyze = selectedFile;
        const formData = new FormData();

        formData.append("image", fileToAnalyze);

        analyzeBtn.disabled = true;
        analyzeBtn.textContent = "Analyzing...";

        resultBox.textContent =
            "🔍 AI is analyzing your image. Please wait...";

        try {
            const response = await fetch("/api/classify", {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error || "Image analysis failed."
                );
            }

            resultBox.textContent = data.result;

        } catch (error) {
            console.error("Classification error:", error);

            resultBox.textContent =
                "❌ " + error.message +
                "\n\nPlease check that the Flask server is running.";

        } finally {
            analyzeBtn.textContent = "Analyze Image";
            analyzeBtn.disabled = !selectedFile;
        }
    });

}
