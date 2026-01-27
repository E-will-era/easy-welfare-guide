import React from 'react';
import Box from '@mui/material/Box';
import footerImage from '../../assets/images/footer_design.png';

export default function Footer() {
    return (
        <Box
            sx={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                width: '100%',
                height: 'auto', // Adjust height based on image aspect ratio or fix it
                maxHeight: '100px', // Keep it reasonable
                overflow: 'visible', // Allow image to potentially stick out or be exact
                backgroundColor: '#39709C', // User requested color
                display: 'flex',
                alignItems: 'end', // Align bottom
                justifyContent: 'center',
                zIndex: 0,
                pointerEvents: 'none' // Ensure it doesn't block clicks if transparent parts exist
            }}
        >
            <img
                src={footerImage}
                alt="Footer"
                style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    maxHeight: '100px'
                }}
            />
        </Box>
    );
}
