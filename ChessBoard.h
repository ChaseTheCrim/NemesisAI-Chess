#ifndef CHESSBOARD_H
#define CHESSBOARD_H

#include <QGraphicsView>
#include <QGraphicsScene>
#include <QGraphicsTextItem>
#include <QProcess>
#include <QJsonObject>
#include <QJsonDocument>
#include <QMap>
#include <QString>
#include <QKeyEvent>
#include <QByteArray>

class ChessPiece;

class ChessBoard : public QGraphicsView {
    Q_OBJECT

public:
    ChessBoard(QWidget *parent = nullptr);
    void attemptMove(ChessPiece* piece, const QString& uciMove);

protected:
    void wheelEvent(QWheelEvent *event) override;
    void mousePressEvent(QMouseEvent *event) override;
    void mouseMoveEvent(QMouseEvent *event) override;
    void mouseReleaseEvent(QMouseEvent *event) override;
    void keyPressEvent(QKeyEvent *event) override;

private slots:
    void readEngineOutput();
    void updateBoardFromFEN(const QString& fen);

private:
    QByteArray m_engineBuffer;
    QGraphicsScene *scene;
    QMap<QString, QPixmap> piecePixmaps;
    QPoint lastPanPoint;

    QProcess *engineProcess;
    ChessPiece *pendingPiece;
    QGraphicsTextItem *m_gameOverText = nullptr;

    void loadAssets();
    void drawBoard();
    void setupInitialPosition();
    void startEngine();
    void showGameOver(const QString& message);
};

#endif // CHESSBOARD_H