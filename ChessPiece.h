#ifndef CHESSPIECE_H
#define CHESSPIECE_H

#include <QGraphicsEllipseItem>
#include <QGraphicsPixmapItem>
#include <QGraphicsSceneMouseEvent>
#include <QString>
#include <QPen> 

class ChessBoard;

class ChessPiece : public QGraphicsEllipseItem {
public:
    ChessPiece(const QString& type, const QPixmap& pixmap, ChessBoard* board, QGraphicsItem *parent = nullptr);

    void snapBack();
    QString getPieceType() const { return pieceType; }

    // enable = true ise hitbox (mavi çerçeve) görünür, resim gizlenir.
    void setDebugView(bool enable); 

protected:
    void mousePressEvent(QGraphicsSceneMouseEvent *event) override;
    void mouseReleaseEvent(QGraphicsSceneMouseEvent *event) override;

private:
    QString pieceType;
    const int squareSize = 16;
    
    QGraphicsPixmapItem* m_sprite; 
    
    int originCol, originRow;
    QPointF originalPos;
    ChessBoard* m_board;

    QString toChessNotation(int col, int row);
};

#endif // CHESSPIECE_H