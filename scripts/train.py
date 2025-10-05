
from src.preprocessing.preprocessor import dataset_read, bulk_preprocessing
from src.llm2vectrain.model import load_llm2vec_model
from src.llm2vectrain.llm2vec_trainer import l2vec_train
from src.models.mlp import build_mlp, load_config
from pathlib import Path
from src.utils.config_loader import DATASET_NPZ
from src.utils.dataset import dataset_splitter, scale_pca_lyrics

import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def train_mlp_model(data : dict):
    """
    Train the MLP model with extracted features.
    
    Parameters
    ----------
        data : dict{np.array}
            A dictionary of np.arrays, containing the train/test/val split.
    """
    logger.info("Starting MLP training...")
    
    # Load MLP configuration
    config = load_config("config/model_config.yml")

    # Destructure the dictionary to get data split
    X_train, y_train = data["train"]
    X_val, y_val     = data["val"]
    X_test, y_test   = data["test"]
    
    # Build and train MLP
    mlp_classifier = build_mlp(input_dim=X_train.shape[1], config=config)
    
    # Show model summary
    mlp_classifier.get_model_summary()
    
    # Train the model
    history = mlp_classifier.train(X_train, y_train, X_val, y_val)
    
    # Load best model and evaluate on test set
    try:
        mlp_classifier.load_model("models/mlp/mlp_best.pth")
        logger.info("Loaded best model for final evaluation")
    except FileNotFoundError:
        logger.warning("Best model not found, using current model")
    
    # Final evaluation
    test_results = mlp_classifier.evaluate(X_test, y_test)

    # Save final model
    mlp_classifier.save_model("models/mlp/mlp_multimodal.pth")
    
    logger.info("MLP training completed successfully!")
    logger.info(f"Final test accuracy: {test_results['test_accuracy']:.2f}%")
    
    return mlp_classifier


def train_pipeline():
    """
    Training script which includes preprocessing, feature extraction, and training the MLP model.

    The train pipeline saves the train dataset in an .npz format.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    # Instantiate X and Y vectors
    X, Y = None, None

    dataset_path = Path(DATASET_NPZ)

    if dataset_path.exists():
        print("Training dataset already exists. Loading file...")

        loaded_data = np.load(DATASET_NPZ)
        X = loaded_data["X"]
        Y = loaded_data["Y"]
    else:
        print("Training dataset does not exist. Processing data...")
        # Get batches from dataset and return full Y labels
        batches, Y = dataset_read(batch_size=50)
        batch_count = 1

        # Instantiate LLM2Vec Model
        l2v = load_llm2vec_model()

        # Preallocate space for the whole concatenated sequence (20,000 samples)
        X = np.zeros((len(Y), 2048), dtype=np.float32)

        start_idx = 0
        for batch in batches:
            audio, lyrics = None, None  # Gets rid of previous values consuming current memory
            
            print(f"Bulk Preprocessing batch {batch_count}...")
            lyrics = bulk_preprocessing(batch, batch_count)
            batch_count += 1

            # Call the train method for LLM2Vec
            print(f"\nStarting LLM2Vec feature extraction...")
            lyric_features = l2vec_train(l2v, lyrics)

            batch_size = lyric_features.shape[0]

            X[start_idx:start_idx + batch_size, :] = lyric_features
            start_idx += batch_size

        # Convert label list into np.array
        Y = np.array(Y)

        logger.info("Saving dataset...")
        np.savez(
            file=DATASET_NPZ,
            X=X,
            Y=Y
        )

    # Run splitting and scaling
    logger.info("Running standard scaling...")
    data = dataset_splitter(X, Y)
    data = scale_pca_lyrics(data)
    
    print("Starting MLP training...")
    train_mlp_model(data)

if __name__ == "__main__":
    train_pipeline()

