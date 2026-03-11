from flask import Flask, request, render_template, redirect, url_for, send_file, jsonify
from PIL import Image
import numpy as np
from sklearn.decomposition import PCA, FastICA
import io
import base64
import math

app = Flask(__name__)

# Calculate PSNR function
def calculate_psnr(original_image, compressed_image):
    mse = np.mean((original_image - compressed_image) ** 2)
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    psnr = 20 * math.log10(max_pixel / math.sqrt(mse))
    return psnr

# Render the technique selection page
@app.route('/')
def select_technique():
    return render_template('select_technique.html')

# Handle technique selection and render index page with selected technique
@app.route('/select_technique', methods=['POST'])
def select_technique_post():
    technique = request.form['technique']
    return render_template('index.html', technique=technique)

#new
@app.route('/technique',methods=['GET', 'POST'])
def technique():
    if request.method == 'POST':
        technique = request.form['technique']
        if technique == 'pca':
            return redirect(url_for('pca_page'))
        elif technique == 'svd':
            return redirect(url_for('svd_page'))
        elif technique == 'ica':
            return redirect(url_for('ica_page'))
    return render_template('technique.html')

@app.route('/pca')
def pca_page():
    return render_template('pca.html')

@app.route('/svd')
def svd_page():
    return render_template('svd.html')

@app.route('/ica')
def ica_page():
    return render_template('ica.html')
#end

# Handle image upload, compression, and PSNR calculation
@app.route('/compress', methods=['POST'])
def compress_image():
    n_components = int(request.form['components'])
    technique = request.form['technique']
    file = request.files['image']
    image = Image.open(file.stream)

    # Convert image to RGB and then to a numpy array
    image_array = np.array(image.convert('RGB'))
    original_image = image_array.copy()

    # Split the image into its RGB components
    r, g, b = image_array[:,:,0], image_array[:,:,1], image_array[:,:,2]

    def apply_pca(channel, n_components):
        original_shape = channel.shape
        flat_channel = channel.reshape(-1, original_shape[1])
        
        # Ensure n_components is within valid range
        max_components = min(flat_channel.shape)
        if n_components > max_components:
            n_components = max_components

        pca = PCA(n_components=n_components)
        compressed_pca = pca.fit_transform(flat_channel)
        decompressed_pca = pca.inverse_transform(compressed_pca)
        decompressed_channel = decompressed_pca.reshape(original_shape)
        return decompressed_channel

    def apply_svd(channel, n_components):
        original_shape = channel.shape
        flat_channel = channel.reshape(-1, original_shape[1])
        
        # Ensure n_components is within valid range
        max_components = min(flat_channel.shape)
        if n_components > max_components:
            n_components = max_components

        u, s, vh = np.linalg.svd(flat_channel, full_matrices=False)
        compressed_svd = np.dot(u[:, :n_components] * s[:n_components], vh[:n_components, :])
        decompressed_svd = compressed_svd.reshape(original_shape)
        return decompressed_svd

    def apply_ica(channel, n_components):
        original_shape = channel.shape
        flat_channel = channel.reshape(-1, original_shape[1])
        
        # Ensure n_components is within valid range
        max_components = min(flat_channel.shape)
        if n_components > max_components:
            n_components = max_components

        ica = FastICA(n_components=n_components, random_state=0)
        compressed_ica = ica.fit_transform(flat_channel)
        decompressed_ica = ica.inverse_transform(compressed_ica)
        decompressed_channel = decompressed_ica.reshape(original_shape)
        return decompressed_channel

    # Apply the selected technique
    if technique == 'PCA':
        r_compressed = apply_pca(r, n_components)
        g_compressed = apply_pca(g, n_components)
        b_compressed = apply_pca(b, n_components)
    elif technique == 'SVD':
        r_compressed = apply_svd(r, n_components)
        g_compressed = apply_svd(g, n_components)
        b_compressed = apply_svd(b, n_components)
    elif technique == 'ICA':
        r_compressed = apply_ica(r, n_components)
        g_compressed = apply_ica(g, n_components)
        b_compressed = apply_ica(b, n_components)
    else:
        return jsonify({'error': 'Invalid technique'})

    # Stack the channels back together
    compressed_img = np.stack((r_compressed, g_compressed, b_compressed), axis=-1)

    # Rescale the decompressed image to the range [0, 255]
    compressed_img_rescaled = np.clip(compressed_img, 0, 255).astype(np.uint8)

    # Convert the numpy array back to an image
    compressed_pil_image = Image.fromarray(compressed_img_rescaled, mode='RGB')
    img_io = io.BytesIO()
    compressed_pil_image.save(img_io, 'JPEG')
    img_io.seek(0)

    # Calculate PSNR
    psnr = calculate_psnr(original_image, compressed_img_rescaled)

    # Encode compressed image to base64
    img_str = base64.b64encode(img_io.getvalue()).decode()

    return jsonify({'image': img_str, 'psnr': psnr})

if __name__ == '__main__':
    app.run(debug=True)
