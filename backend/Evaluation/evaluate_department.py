import os
import asyncio
import pandas as pd
import os
import sys

# Add backend folder to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

import seaborn as sns
import matplotlib.pyplot as plt

from app.pipeline.department_classifier import classify_department


GROUND_TRUTH = "Evaluation/ground_truth.csv"


async def predict_department(filepath):

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    pred = await classify_department(text)
    return pred


async def evaluate():

    df = pd.read_csv(GROUND_TRUTH)

    y_true = []
    y_pred = []

    for _, row in df.iterrows():

        filepath = row["filepath"]

        true_label = row["department"]

        pred = await predict_department(filepath)

        print(f"{os.path.basename(filepath)}")
        print(f"True      : {true_label}")
        print(f"Predicted : {pred}")
        print("-" * 40)

        y_true.append(true_label)
        y_pred.append(pred)

    print("\n========== RESULTS ==========\n")

    print("Accuracy :", accuracy_score(y_true, y_pred))

    print(
        "Precision:",
        precision_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0,
        ),
    )

    print(
        "Recall:",
        recall_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0,
        ),
    )

    print(
        "F1 Score:",
        f1_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0,
        ),
    )

    print("\nClassification Report\n")

    print(
        classification_report(
            y_true,
            y_pred,
            zero_division=0,
        )
    )

    labels = [
        "Finance",
        "HR",
        "Legal",
        "Security",
        "Operations",
        "Engineering",
    ]

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=labels,
    )

    plt.figure(figsize=(8, 6))

    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        xticklabels=labels,
        yticklabels=labels,
        cmap="Blues",
    )

    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Department Classification Confusion Matrix")

    plt.tight_layout()

    plt.savefig("Evaluation/confusion_matrix.png")

    print("\nSaved confusion_matrix.png")


if __name__ == "__main__":
    asyncio.run(evaluate())